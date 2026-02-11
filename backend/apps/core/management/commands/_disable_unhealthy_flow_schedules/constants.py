# -*- coding: utf-8 -*-
from enum import Enum


class Querys(Enum):
    FLOWS_FAILED_LAST_WEEK = """
    query($since: timestamptz!) {
    flow(
    where: {
    schedule: { _is_null: false }
    is_schedule_active: {_eq: true}
    archived: {_eq: false}
    flow_runs: {
        state: { _eq: "Failed" }
        start_time: { _gte: $since }
    }
    }
    ) {
    id
    created
    name
    }
    }
    """

    LAST_COMPLETED_RUNS_TASKS = """
    query LastTwoCompletedRunsWithTasks($flow_id: uuid!) {
    flow_run(
    where: {
    flow_id: { _eq: $flow_id }
    state: { _in: ["Success", "Failed"] }
    }
    order_by: { start_time: desc }
    limit: 2
    ) {
    id
    name
    start_time
    state
    task_runs(
    where: {
    state: { _in: ["Failed"] }
    }
    order_by: { start_time: desc }
    limit: 1) {
    id
    state
    end_time
    state_message
    task {
    id
    name
    }
    }
    }
    }
    """


class Constants(Enum):
    TASKS_NAME_DISABLE = ("run_dbt",)
    FLOW_SUCCESS_STATE = "Success"
    FLOW_FAILED_STATE = "Failed"

    PREFECT_URL = "https://prefect.basedosdados.org/"
    PREFECT_URL_FLOW = PREFECT_URL + "flow/"
    PREFECT_URL_API = PREFECT_URL + "api"

    DISCORD_ROLE_DADOS = "865034571469160458"
    TEXT_FLOW_FORMAT = "- {run_name} | Last failure `{task_name}` | {link}"

    STATE_MESSAGE_IGNORE = (
        "No heartbeat detected from the remote task; marking the run as failed.",
    )
