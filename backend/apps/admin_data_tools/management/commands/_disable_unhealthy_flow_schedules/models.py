# -*- coding: utf-8 -*-
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from .constants import Constants
from .datetime_utils import parse_datetime

if TYPE_CHECKING:
    from .service import FlowService


class Task:
    """Represents a Prefect task."""

    def __init__(self, id: str, name: str) -> None:
        """Args:
        id: Prefect task UUID.
        name: Task name.
        """
        self.id = id
        self.name = name


class TaskRun:
    """Represents a single run of a Prefect task."""

    def __init__(
        self,
        id: str,
        state: str,
        end_time: Optional[str],
        state_message: str,
        task: dict,
    ) -> None:
        """Args:
        id: Prefect task run UUID.
        state: Run state (e.g. ``"Failed"``).
        end_time: ISO 8601 end timestamp, or ``None`` if not finished.
        state_message: Human-readable state message from Prefect.
        task: Raw task dict with ``id`` and ``name`` keys.
        """
        self.id = id
        self.state = state
        self.end_time = end_time
        self.state_message = state_message
        self.task = Task(**task)


class FlowRun:
    """Represents a single run of a Prefect flow."""

    def __init__(
        self,
        id: str,
        name: str,
        start_time: str,
        state: str,
        task_runs: list,
    ) -> None:
        """Args:
        id: Prefect flow run UUID.
        name: Flow run name.
        start_time: ISO 8601 start timestamp.
        state: Run state (e.g. ``"Success"`` or ``"Failed"``).
        task_runs: List of raw task run dicts. Only the first entry is used.
        """
        self.id = id
        self.name = name
        self.start_time = parse_datetime(start_time)
        self.state = state
        self.task_runs = TaskRun(**task_runs[0]) if task_runs else None


class FlowDisable:
    """Represents a Prefect flow candidate for disabling.

    On instantiation, fetches the last two completed runs from the Prefect API
    to support validation.
    """

    def __init__(
        self,
        id: str,
        created: str | datetime,
        service: "FlowService",
        name: str = "",
    ) -> None:
        """Args:
        id: Prefect flow UUID.
        created: The earliest timestamp from which failures are considered
            relevant — either an ISO 8601 string or a datetime. For new
            flows this is Prefect's ``created`` field; for flows reactivated
            by an admin, ``reactivated_at`` is passed instead.
        service: ``FlowService`` instance used to fetch run data.
        name: Flow name. Defaults to empty string.
        """
        self.id = id
        self.name = name
        self.valid_since = parse_datetime(created) if isinstance(created, str) else created
        self.service = service
        self.runs = self.get_runs()

    def get_runs(self) -> list[FlowRun]:
        """Fetch the last two completed runs for this flow from the Prefect API.

        Returns:
            List of up to two ``FlowRun`` objects ordered by start time descending.
        """
        response = self.service.last_completed_runs_tasks(self.id)
        return [FlowRun(**run) for run in response["flow_run"]]

    def validate(self) -> bool:
        """Determine whether this flow should be disabled.

        A flow is considered unhealthy — and should be disabled — when either
        of the following conditions holds after ``self.valid_since``:

        - The last run failed on a ``run_dbt`` task with a non-ignorable error.
        - The last two runs both failed.

        Returns:
            ``True`` if the flow should be disabled, ``False`` otherwise.
        """
        last_run = self.runs[0]
        next_last = self.runs[1] if len(self.runs) == 2 else None

        failed = Constants.FLOW_FAILED_STATE.value
        dbt_failed_after_created = (
            last_run.state == failed
            and last_run.task_runs.task.name in Constants.TASKS_NAME_DISABLE.value
            and last_run.start_time >= self.valid_since
            and last_run.task_runs.state_message not in Constants.STATE_MESSAGE_IGNORE.value
        )

        consecutive_failed_after_created = (
            next_last
            and last_run.state == failed
            and next_last.state == failed
            and max(last_run.start_time, next_last.start_time) >= self.valid_since
        )

        return bool(dbt_failed_after_created or consecutive_failed_after_created)
