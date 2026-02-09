# -*- coding: utf-8 -*-
from typing import TYPE_CHECKING, Optional

from .constants import Constants
from .datetime_utils import parse_datetime

if TYPE_CHECKING:
    from .service import FlowService


class Task:
    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name


class TaskRun:
    def __init__(
        self,
        id: str,
        state: str,
        end_time: Optional[str],
        state_message: str,
        task: dict,
    ):
        self.id = id
        self.state = state
        self.end_time = end_time
        self.state_message = state_message
        self.task = Task(**task)


class FlowRun:
    def __init__(
        self,
        id: str,
        name: str,
        start_time: str,
        state: str,
        task_runs: list,
    ):
        self.id = id
        self.name = name
        self.start_time = parse_datetime(start_time)
        self.state = state
        self.task_runs = (
            TaskRun(**task_runs[0]) if task_runs else None
        )  # Caso não tenha segundo Run


class FlowDisable:
    def __init__(self, id: str, created: str, service: "FlowService"):
        self.id = id
        self.created = parse_datetime(created)
        self.service = service
        self.runs = self.get_runs()

    def get_runs(self):
        response = self.service.last_completed_runs_tasks(self.id)
        return [FlowRun(**run) for run in response["flow_run"]]

    def validate(self) -> bool:
        last_run = self.runs[0]
        next_last = self.runs[1] if len(self.runs) == 2 else None

        failed = Constants.FLOW_FAILED_STATE.value
        dbt_failed_after_created = (
            last_run.state == failed
            and last_run.task_runs.task.name in Constants.TASKS_NAME_DISABLE.value
            and last_run.start_time >= self.created
            and last_run.task_runs.state_message not in Constants.STATE_MESSAGE_IGNORE.value
        )

        consecutive_failed_after_created = (
            next_last
            and last_run.state == failed
            and next_last.state == failed
            and max(last_run.start_time, next_last.start_time) >= self.created
        )

        return bool(dbt_failed_after_created or consecutive_failed_after_created)
