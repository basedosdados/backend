# -*- coding: utf-8 -*-
"""Constantes usadas pelas views de admin_data_tools."""

# field.field_type (BigQuery client) reports legacy SQL names (INTEGER,
# FLOAT, RECORD, ...); the API's `bigquery_type` catalog uses standard SQL
# names (INT64, FLOAT64, STRUCT, BOOLEAN, ...) — only these three actually
# differ, everything else (STRING, BOOLEAN, DATE, TIMESTAMP, ...) is spelled
# the same on both sides.
BQ_LEGACY_TYPE_ALIASES: dict[str, str] = {
    "integer": "int64",
    "float": "float64",
    "record": "struct",
}

FAILED_STATES = {"Failed", "Crashed"}
DBT_TASK_NAMES = {"run_dbt"}
STATE_MESSAGES_IGNORE = {
    "No heartbeat detected from the remote task; marking the run as failed.",
}
