# -*- coding: utf-8 -*-
import os
from typing import Dict

from django.db.models import Q
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport
from loguru import logger

from backend.apps.admin_data_tools.models import DisabledFlowSchedule
from backend.custom.client import send_discord_message

from .constants import Constants, Querys
from .datetime_utils import one_week_ago
from .models import FlowDisable

logger = logger.bind(module="admin_data_tools")


class MakeClient:
    """Builds an authenticated GraphQL client for the Prefect API."""

    def __init__(self) -> None:
        self.graphql_url = Constants.PREFECT_URL_API.value
        self.query = self.make_client({"Authorization": f"Bearer {os.getenv('API_KEY_PREFECT')}"})

    def make_client(self, headers: Dict[str, str] = None) -> Client:
        """Instantiate a GQL ``Client`` with the given headers.

        Args:
            headers: HTTP headers to attach to every request.

        Returns:
            Configured ``gql.Client`` instance.
        """
        transport = RequestsHTTPTransport(url=self.graphql_url, headers=headers, use_json=True)
        return Client(transport=transport, fetch_schema_from_transport=False)


class FlowService:
    """Orchestrates detection and disabling of unhealthy Prefect flow schedules."""

    def __init__(self) -> None:
        self.client = MakeClient()

    # ------------------------------------------------------------------
    # Prefect API helpers
    # ------------------------------------------------------------------

    def flows_failed_last_week(self) -> list[dict]:
        """Query Prefect for active flows that had at least one failed run in the past week.

        Returns:
            List of dicts with ``id``, ``created``, and ``name`` keys.
        """
        since = one_week_ago()
        response = self.client.query.execute(
            gql(Querys.FLOWS_FAILED_LAST_WEEK.value), variable_values={"since": since}
        )
        return [
            {"id": fail["id"], "created": fail["created"], "name": fail["name"]}
            for fail in response["flow"]
        ]

    def active_flows_by_names(self, names: list[str]) -> list[dict]:
        """Query Prefect for flows that are currently active, filtered by name.

        Args:
            names: List of flow names to look up.

        Returns:
            List of dicts with ``id`` and ``name`` keys.
        """
        response = self.client.query.execute(
            gql(Querys.ACTIVE_FLOWS_BY_NAMES.value), variable_values={"names": names}
        )
        return response["flow"]

    def last_completed_runs_tasks(self, flow_id: str) -> dict:
        """Fetch the last two completed (Success or Failed) runs for a flow.

        Args:
            flow_id: Prefect flow UUID.

        Returns:
            Raw GraphQL response dict containing a ``flow_run`` list.
        """
        return self.client.query.execute(
            gql(Querys.LAST_COMPLETED_RUNS_TASKS.value), variable_values={"flow_id": flow_id}
        )

    def set_flow_schedule(self, flow_id: str, active: bool) -> dict:
        """Toggle a flow's schedule on or off in Prefect.

        Args:
            flow_id: Prefect flow UUID.
            active: ``True`` to activate the schedule, ``False`` to deactivate.

        Returns:
            Raw GraphQL response dict.
        """
        mutation_name = "set_schedule_active" if active else "set_schedule_inactive"
        query = f"""
        mutation SetFlowSchedule($flow_id: UUID!) {{
          {mutation_name}(
            input: {{
              flow_id: $flow_id
            }}
          ) {{
            success
          }}
        }}
        """
        return self.client.query.execute(gql(query), variable_values={"flow_id": flow_id})

    def disable_flow_schedule(self, flow_id: str) -> None:
        """Disable a flow schedule, calling the mutation twice as a Prefect workaround.

        Note:
            Prefect 0.15 has a bug where a single ``set_schedule_inactive`` call
            is not always effective. Two consecutive calls are required.

        Args:
            flow_id: Prefect flow UUID to disable.
        """
        for _ in range(2):
            self.set_flow_schedule(flow_id=flow_id, active=False)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def disable_unhealthy_flow_schedules(self) -> None:
        """Run both phases of the unhealthy-flow detection and disabling pipeline.

        Phase 1 — enforce known-disabled flows: re-disables flows that Prefect
        reactivated (e.g. after re-registration) and detects new failures in
        flows that an admin previously reactivated.

        Phase 2 — detect new unhealthy flows: queries Prefect for flows that
        failed in the past week, validates each one, disables the unhealthy
        ones, and sends a Discord notification.
        """
        self._enforce_disabled_flows()
        self._detect_and_disable_new_flows()

    # ------------------------------------------------------------------
    # Phase 1
    # ------------------------------------------------------------------

    def _enforce_disabled_flows(self) -> None:
        """Re-disable tracked flows that Prefect reactivated.

        Also checks reactivated flows for new failures since reactivation.
        """
        all_tracked = list(
            DisabledFlowSchedule.objects.filter(
                Q(is_schedule_active=False) | Q(reactivated_at__isnull=False)
            )
        )
        if not all_tracked:
            return

        tracked_by_name = {record.flow_name: record for record in all_tracked}
        active_in_prefect = self.active_flows_by_names(list(tracked_by_name.keys()))
        active_by_name = {flow["name"]: flow["id"] for flow in active_in_prefect}

        for flow_name, record in tracked_by_name.items():
            if flow_name not in active_by_name:
                continue
            self._process_active_tracked_flow(record, active_by_name[flow_name])

    def _process_active_tracked_flow(
        self, record: DisabledFlowSchedule, current_flow_id: str
    ) -> None:
        """Sync the stored flow ID and apply the appropriate enforcement action.

        Args:
            record: The ``DisabledFlowSchedule`` database record.
            current_flow_id: The flow's current UUID in Prefect.
        """
        self._sync_flow_id(record, current_flow_id)

        if not record.is_schedule_active:
            self._re_disable_flow(record, current_flow_id)
        elif record.reactivated_at:
            self._check_post_reactivation(record, current_flow_id)

    def _sync_flow_id(self, record: DisabledFlowSchedule, current_flow_id: str) -> None:
        """Update the stored flow ID if Prefect re-registered the flow with a new UUID.

        Args:
            record: The ``DisabledFlowSchedule`` database record.
            current_flow_id: The flow's current UUID in Prefect.
        """
        if record.flow_id == current_flow_id:
            return
        record.flow_id = current_flow_id
        record.save(update_fields=["flow_id"])

    def _re_disable_flow(self, record: DisabledFlowSchedule, current_flow_id: str) -> None:
        """Disable a flow that should remain inactive but was reactivated by Prefect.

        Args:
            record: The ``DisabledFlowSchedule`` database record.
            current_flow_id: The flow's current UUID in Prefect.
        """
        self.disable_flow_schedule(flow_id=current_flow_id)
        logger.info(f"Re-disabled flow {record.flow_name} ({current_flow_id})")

    def _check_post_reactivation(self, record: DisabledFlowSchedule, current_flow_id: str) -> None:
        """Disable a flow if it broke again after being reactivated by an admin.

        Uses ``reactivated_at`` as the baseline timestamp instead of Prefect's
        ``created`` field, which is unreliable after re-registration.

        Args:
            record: The ``DisabledFlowSchedule`` database record.
            current_flow_id: The flow's current UUID in Prefect.
        """
        flow_disable = FlowDisable(
            id=current_flow_id,
            created=record.reactivated_at.isoformat(),
            service=self,
        )
        if not flow_disable.validate():
            return
        self.disable_flow_schedule(flow_id=current_flow_id)
        record.is_schedule_active = False
        record.reactivated_at = None
        record.save(update_fields=["is_schedule_active", "reactivated_at"])
        logger.info(f"Re-disabled flow {record.flow_name} after reactivation failure")

    # ------------------------------------------------------------------
    # Phase 2
    # ------------------------------------------------------------------

    def _detect_and_disable_new_flows(self) -> None:
        """Detect untracked unhealthy flows, disable them, and send a notification."""
        flows = self._get_new_untracked_flows()
        flows_to_disable = [flow for flow in flows if flow.validate()]

        if not flows_to_disable:
            return

        for flow in flows_to_disable:
            self._disable_and_register(flow)

        self._send_disable_notification(flows, flows_to_disable)

    def _get_new_untracked_flows(self) -> list[FlowDisable]:
        """Return flows that failed last week but are not yet tracked in the database.

        Returns:
            List of ``FlowDisable`` instances for untracked failing flows.
        """
        flows_data = self.flows_failed_last_week()
        tracked_names = set(DisabledFlowSchedule.objects.values_list("flow_name", flat=True))
        return [
            FlowDisable(**flow, service=self)
            for flow in flows_data
            if flow["name"] not in tracked_names
        ]

    def _disable_and_register(self, flow: FlowDisable) -> None:
        """Disable a flow in Prefect and create its tracking record in the database.

        Args:
            flow: The ``FlowDisable`` instance to disable and register.
        """
        self.disable_flow_schedule(flow_id=flow.id)
        DisabledFlowSchedule.objects.create(flow_name=flow.name, flow_id=flow.id)

    def _send_disable_notification(
        self, flows_in_alert: list[FlowDisable], flows_disabled: list[FlowDisable]
    ) -> None:
        """Send a Discord notification summarising flows in alert and newly disabled flows.

        Splits the message into chunks of at most 2000 characters to respect
        Discord's per-message limit.

        Args:
            flows_in_alert: All untracked failing flows (warning list).
            flows_disabled: Flows that were disabled in this run.
        """
        message_parts = [
            self.format_flows("🚨 Flows em alerta", flows_in_alert),
            self.format_flows(
                f"⛔ Flows desativados <@&{Constants.DISCORD_ROLE_DADOS.value}>",
                flows_disabled,
            ),
        ]
        for chunk in self._split_message("\n\n".join(message_parts)):
            send_discord_message(chunk)

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _split_message(message: str, limit: int = 2000) -> list[str]:
        """Split a message into chunks that do not exceed ``limit`` characters.

        Splits on line boundaries to avoid cutting lines in the middle.

        Args:
            message: The full message string to split.
            limit: Maximum number of characters per chunk. Defaults to 2000.

        Returns:
            List of message chunks, each at most ``limit`` characters long.
        """
        chunks, current = [], ""
        for line in message.splitlines(keepends=True):
            if len(current) + len(line) > limit:
                chunks.append(current)
                current = ""
            current += line
        if current:
            chunks.append(current)
        return chunks

    @staticmethod
    def format_flows(title: str, flows: list[FlowDisable]) -> str:
        """Format a list of flows as a Discord markdown block.

        Args:
            title: Section heading displayed in bold.
            flows: List of ``FlowDisable`` instances to format.

        Returns:
            Formatted string with one line per flow, or a ``_(nenhum)_``
            placeholder when the list is empty.
        """
        if not flows:
            return f"**{title}**\n_(nenhum)_"

        lines = [f"**{title}**"]
        for flow in flows:
            link = Constants.PREFECT_URL_FLOW.value + flow.id
            last_run = flow.runs[0]
            if last_run.task_runs:
                lines.append(
                    Constants.TEXT_FLOW_FORMAT.value.format(
                        task_name=last_run.task_runs.task.name,
                        run_name=last_run.name,
                        link=link,
                    )
                )
        return "\n".join(lines)
