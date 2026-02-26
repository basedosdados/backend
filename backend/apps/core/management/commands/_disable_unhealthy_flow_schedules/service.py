# -*- coding: utf-8 -*-
import os
from typing import Dict

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport
from loguru import logger

from backend.custom.client import send_discord_message

from .constants import Constants, Querys
from .datetime_utils import one_week_ago
from .models import FlowDisable

logger = logger.bind(module="core")


class MakeClient:
    def __init__(self):
        self.graphql_url = Constants.PREFECT_URL_API.value
        self.query = self.make_client({"Authorization": f"Bearer {os.getenv('API_KEY_PREFECT')}"})

    def make_client(self, headers: Dict[str, str] = None) -> Client:
        transport = RequestsHTTPTransport(url=self.graphql_url, headers=headers, use_json=True)

        return Client(transport=transport, fetch_schema_from_transport=False)


class FlowService:
    def __init__(self):
        self.client = MakeClient()

    def flows_failed_last_week(self) -> list:
        since = one_week_ago()

        variables = {"since": since}

        response = self.client.query.execute(
            gql(Querys.FLOWS_FAILED_LAST_WEEK.value), variable_values=variables
        )

        return [{"id": fail["id"], "created": fail["created"]} for fail in response["flow"]]

    def last_completed_runs_tasks(self, flow_id: str):
        variables = {"flow_id": flow_id}

        return self.client.query.execute(
            gql(Querys.LAST_COMPLETED_RUNS_TASKS.value), variable_values=variables
        )

    def set_flow_schedule(self, flow_id: str, active: bool):
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

        variables = {"flow_id": flow_id}

        return self.client.query.execute(gql(query), variable_values=variables)

    def disable_unhealthy_flow_schedules(self) -> None:
        flows_data = self.flows_failed_last_week()

        flows = [FlowDisable(**flow, service=self) for flow in flows_data]

        flows_to_disable = [flow for flow in flows if flow.validate()]

        if flows_to_disable:
            for flow in flows_to_disable:
                for _ in range(2):  # Existe um bug onde o Flow não desativa com apenas uma query
                    self.set_flow_schedule(flow_id=flow.id, active=False)

            message_parts = [
                self.format_flows("🚨 Flows em alerta", flows),
                self.format_flows(
                    f"⛔ Flows desativados <@&{Constants.DISCORD_ROLE_DADOS.value}>",
                    flows_to_disable,
                ),
            ]

            send_discord_message("\n\n".join(message_parts))

    @staticmethod
    def format_flows(title: str, flows: list) -> str:
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
