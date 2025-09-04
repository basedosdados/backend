# -*- coding: utf-8 -*-
import json
import os
from collections.abc import Callable
from functools import cache, wraps
from typing import Any, Literal, Self

import httpx
from google.api_core.exceptions import GoogleAPICallError
from google.cloud import bigquery as bq
from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, model_validator

# HTTPX Default Timeout
TIMEOUT = 5.0

# HTTPX Read Timeout
READ_TIMEOUT = 60.0

# Maximum number of datasets returned on search
PAGE_SIZE = 10

# 5GB limit for inspection queries
LIMIT_INSPECTION_QUERY = int(5 * 1e9)

# 10GB limit for other queries
LIMIT_BIGQUERY_QUERY = int(10 * 1e9)

# URL for searching datasets
SEARCH_URL = "https://backend.basedosdados.org/search/"

# URL for fetching dataset details
GRAPHQL_URL = "https://backend.basedosdados.org/graphql"

# GraphQL query for fetching dataset details
DATASET_DETAILS_QUERY = """
query GetDatasetOverview($id: ID!) {
    allDataset(id: $id, first: 1) {
        edges {
            node {
                id
                name
                slug
                description
                organizations {
                    edges {
                        node {
                            name
                            slug
                        }
                    }
                }
                themes {
                    edges {
                        node {
                            name
                        }
                    }
                }
                tags {
                    edges {
                        node {
                            name
                        }
                    }
                }
                tables {
                    edges {
                        node {
                            id
                            name
                            slug
                            description
                            cloudTables {
                                edges {
                                    node {
                                        gcpProjectId
                                        gcpDatasetId
                                        gcpTableId
                                    }
                                }
                            }
                            columns {
                                edges {
                                    node {
                                        id
                                        name
                                        description
                                        bigqueryType {
                                            name
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
"""


class GoogleAPIError:
    """Constants for expected Google API error types."""

    BYTES_BILLED_LIMIT_EXCEEDED = "bytesBilledLimitExceeded"
    NOT_FOUND = "notFound"


class Column(BaseModel):
    """Represents a column in a BigQuery table with metadata."""

    name: str
    type: str
    description: str | None


class Table(BaseModel):
    """Represents a BigQuery table with its columns and metadata."""

    id: str
    gcp_id: str | None
    name: str
    slug: str | None
    description: str | None
    columns: list[Column]


class DatasetOverview(BaseModel):
    """Basic dataset information without table details."""

    id: str
    name: str
    slug: str | None
    description: str | None
    tags: list[str]
    themes: list[str]
    organizations: list[str]


class Dataset(DatasetOverview):
    """Complete dataset information including all tables and columns."""

    tables: list[Table]


class ErrorDetails(BaseModel):
    "Error response format."

    error_type: str | None = None
    message: str
    instructions: str | None = None


class ToolError(Exception):
    """Custom exception for tool-specific errors."""

    def __init__(
        self, message: str, error_type: str | None = None, instructions: str | None = None
    ):
        super().__init__(message)
        self.error_type = error_type
        self.instructions = instructions


class ToolOutput(BaseModel):
    """Tool output response format."""

    status: Literal["success", "error"]
    results: Any | None = None
    error_details: ErrorDetails | None = None

    @model_validator(mode="after")
    def check_passwords_match(self) -> Self:
        if (self.results is None) ^ (self.error_details is None):
            return self
        raise ValueError("Only one of 'results' or 'error_details' should be set")


def handle_tool_errors(
    _func: Callable[..., Any] | None = None,
    *,
    instructions: dict[str, str] = {},
) -> Callable[..., Any]:
    """Decorator that catches errors in a tool function and returns them as structured JSON.

    Args:
        _func (Callable[..., Any] | None, optional): Function to wrap.
            Set automatically when used as a decorator. Defaults to None.
        instructions (dict[str, str], optional): Maps known error reasons
            from Google API to recovery instructions. If a reason matches,
            the instruction is added to the error JSON.

    Returns:
        Callable[..., Any]: Wrapped function that returns the tool result on success
            or structured error JSON on failure.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except GoogleAPICallError as e:
                if e.errors:
                    reason = e.errors[0].get("reason")
                    message = e.errors[0].get("message", str(e))

                error_details = ErrorDetails(
                    error_type=reason, message=message, instructions=instructions.get(reason)
                )
            except ToolError as e:
                error_details = ErrorDetails(
                    error_type=e.error_type, message=str(e), instructions=e.instructions
                )
            except Exception as e:
                error_details = ErrorDetails(message=f"Unexpected error: {e}")

            tool_output = ToolOutput(status="error", error_details=error_details).model_dump(
                exclude_none=True
            )
            return json.dumps(tool_output, ensure_ascii=False, indent=2)

        return wrapper

    if _func is None:
        return decorator

    return decorator(_func)


@cache
def get_bigquery_client() -> bq.Client:
    return bq.Client(project=os.environ["QUERY_PROJECT_ID"])


@tool
@handle_tool_errors
def search_datasets(query: str) -> str:
    """Search for datasets in Base dos Dados using keywords.

    CRITICAL: Use individual KEYWORDS only, not full sentences. The search engine uses Elasticsearch.

    Args:
        query (str): 2-3 keywords maximum. Use Portuguese terms, organization acronyms, or dataset acronyms.
            Good Examples: "censo", "educacao", "ibge", "inep", "rais", "saude"
            Avoid: "Brazilian population data by municipality"

    Returns:
        str: JSON array of datasets. If empty/irrelevant results, try different keywords.

    Strategy: Start with broad terms like "censo", "ibge", "inep", "rais", then get specific if needed.
    Next step: Use `get_dataset_details()` with returned dataset IDs.
    """  # noqa: E501
    with httpx.Client() as client:
        response = client.get(
            url=SEARCH_URL,
            params={"q": query, "page_size": PAGE_SIZE},
            timeout=httpx.Timeout(TIMEOUT, read=READ_TIMEOUT),
        )
        response.raise_for_status()
        data: dict = response.json()

    datasets = data.get("results", [])

    overviews = []

    for dataset in datasets:
        dataset_overview = DatasetOverview(
            id=dataset["id"],
            name=dataset["name"],
            slug=dataset.get("slug"),
            description=dataset.get("description"),
            tags=[tag["name"] for tag in dataset.get("tags", [])],
            themes=[theme["name"] for theme in dataset.get("themes", [])],
            organizations=[org["name"] for org in dataset.get("organizations", [])],
        )
        overviews.append(dataset_overview.model_dump())

    tool_output = ToolOutput(status="success", results=overviews).model_dump(exclude_none=True)
    return json.dumps(tool_output, ensure_ascii=False, indent=2)


@tool
@handle_tool_errors
def get_dataset_details(dataset_id: str) -> str:
    """Get comprehensive details about a specific dataset including all tables and columns.

    Use AFTER `search_datasets()` to understand data structure before writing queries.

    Args:
        dataset_id (str): Dataset ID obtained from `search_datasets()`.
            This is typically a UUID-like string, not the human-readable name.

    Returns:
        str: JSON object with complete dataset information, including:
            - Basic metadata (name, description, tags, themes, organizations)
            - tables: Array of all tables in the dataset with:
                - gcp_id: Full BigQuery table reference (`project.dataset.table`)
                - columns: All column names, types, and descriptions
                - table descriptions explaining what each table contains

    Next step: Use `execute_bigquery_sql()` to execute queries.
    """  # noqa: E501
    with httpx.Client() as client:
        response = client.post(
            url=GRAPHQL_URL,
            json={
                "query": DATASET_DETAILS_QUERY,
                "variables": {"id": dataset_id},
            },
            timeout=httpx.Timeout(TIMEOUT, read=READ_TIMEOUT),
        )
        response.raise_for_status()
        data: dict[str, dict[str, dict]] = response.json()

    all_datasets = data.get("data", {}).get("allDataset") or {}
    dataset_edges = all_datasets.get("edges", [])

    if not dataset_edges:
        raise ToolError(
            message=f"Dataset {dataset_id} not found",
            error_type="DATASET_NOT_FOUND",
            instructions="Verify the dataset ID from `search_datasets` results",
        )

    dataset = dataset_edges[0]["node"]

    dataset_id = dataset["id"]
    dataset_name = dataset["name"]
    dataset_slug = dataset.get("slug")
    dataset_description = dataset.get("description")

    # Tags
    dataset_tags = []
    for edge in dataset.get("tags", {}).get("edges", []):
        if tag := edge.get("node", {}).get("name"):
            dataset_tags.append(tag)

    # Themes
    dataset_themes = []
    for edge in dataset.get("themes", {}).get("edges", []):
        if theme := edge.get("node", {}).get("name"):
            dataset_themes.append(theme)

    # Organizations
    dataset_organizations = []
    for edge in dataset.get("organizations", {}).get("edges", []):
        if org := edge.get("node", {}).get("name"):
            dataset_organizations.append(org)

    # Tables
    dataset_tables = []
    for edge in dataset.get("tables", {}).get("edges", []):
        table = edge["node"]

        table_id = table["id"]
        table_name = table["name"]
        table_slug = table.get("slug")
        table_description = table.get("description")

        cloud_table_edges = table["cloudTables"]["edges"]
        if cloud_table_edges:
            cloud_table = cloud_table_edges[0]["node"]
            gcp_project_id = cloud_table["gcpProjectId"]
            gcp_dataset_id = cloud_table["gcpDatasetId"]
            gcp_table_id = cloud_table["gcpTableId"]
            table_gcp_id = f"{gcp_project_id}.{gcp_dataset_id}.{gcp_table_id}"
        else:
            table_gcp_id = None

        table_columns = []
        for edge in table["columns"]["edges"]:
            column = edge["node"]
            table_columns.append(
                Column(
                    name=column["name"],
                    type=column["bigqueryType"]["name"],
                    description=column.get("description"),
                )
            )

        dataset_tables.append(
            Table(
                id=table_id,
                gcp_id=table_gcp_id,
                name=table_name,
                slug=table_slug,
                description=table_description,
                columns=table_columns,
            )
        )

    dataset = Dataset(
        id=dataset_id,
        name=dataset_name,
        slug=dataset_slug,
        description=dataset_description,
        tags=dataset_tags,
        themes=dataset_themes,
        organizations=dataset_organizations,
        tables=dataset_tables,
    ).model_dump()

    tool_output = ToolOutput(status="success", results=dataset).model_dump(exclude_none=True)
    return json.dumps(tool_output, ensure_ascii=False, indent=2)


@tool
@handle_tool_errors(
    instructions={
        GoogleAPIError.BYTES_BILLED_LIMIT_EXCEEDED: "Add WHERE filters or select fewer columns."
    }
)
def execute_bigquery_sql(sql_query: str) -> str:
    """Execute a SQL query against BigQuery tables from the Base dos Dados database.

    Use AFTER identifying the right datasets and understanding tables structure.
    It includes a 10GB processing limit for safety.

    Args:
        sql_query (str): Standard GoogleSQL query. Must reference
            tables using their full `gcp_id` from `get_dataset_details()`.

    Best practices:
        - Use fully qualified names: `project.dataset.table`
        - Select only needed columns, avoid `SELECT *`
        - Add `LIMIT` for exploration
        - Filter early with `WHERE` clauses
        - Order by relevant columns
        - Never use DDL/DML commands
        - Use appropriate data types in comparisons

    Returns:
        str: Query results as JSON array. Empty results return "[]".
    """  # noqa: E501
    forbidden_commands = [
        "CREATE",
        "ALTER",
        "DROP",
        "TRUNCATE",
        "INSERT",
        "UPDATE",
        "DELETE",
        "GRANT",
        "REVOKE",
    ]

    for command in forbidden_commands:
        if command in sql_query.upper():
            raise ToolError(
                message=f"Query aborted: Command {command} is forbidden.",
                error_type="FORBIDDEN_COMMAND",
                instructions="Your access is strictly read-only. Use only SELECT statements.",
            )

    client = get_bigquery_client()

    job_config = bq.QueryJobConfig(maximum_bytes_billed=LIMIT_BIGQUERY_QUERY)
    query_job = client.query(sql_query, job_config=job_config)

    rows = query_job.result()
    results = [dict(row) for row in rows]

    tool_output = ToolOutput(status="success", results=results).model_dump(exclude_none=True)
    return json.dumps(tool_output, ensure_ascii=False, default=str)


@tool
@handle_tool_errors(
    instructions={
        GoogleAPIError.NOT_FOUND: (
            "Dictionary table not found for this dataset. Use `inspect_column_values` instead."
        )
    }
)
def decode_table_values(table_gcp_id: str, column_name: str | None = None) -> str:
    """Decode coded values from a table.

    Use when column values appear to be codes (e.g., 1,2,3 or A,B,C).
    Many datasets use codes for storage efficiency. This tool provides
    the authoritative meanings of these codes.

    Args:
        table_gcp_id (str): Full BigQuery table reference
        column_name (str | None, optional): Column with coded values. If `None`,
            all columns will be used. Defaults to `None`.

    Returns:
        str: JSON array with chave (code) and valor (meaning) mappings.
    """
    # noqa: E501
    try:
        project_name, dataset_name, table_name = table_gcp_id.split(".")
    except ValueError:
        raise ToolError(
            message=f"Invalid table reference: '{table_gcp_id}'",
            error_type="INVALID_TABLE_REFERENCE",
            instructions="Provide a valid table reference in the format `project.dataset.table`",
        )

    client = get_bigquery_client()

    dataset_id = f"{project_name}.{dataset_name}"
    dict_table_id = f"{dataset_id}.dicionario"

    search_query = f"""
        SELECT nome_coluna, chave, valor
        FROM {dict_table_id}
        WHERE id_tabela = '{table_name}'
    """

    if column_name is not None:
        search_query += f"AND nome_coluna = '{column_name}'"

    search_query += "ORDER BY nome_coluna, chave"

    rows = client.query(search_query).result()
    results = [dict(row) for row in rows]

    tool_output = ToolOutput(status="success", results=results).model_dump(exclude_none=True)
    return json.dumps(tool_output, ensure_ascii=False, default=str)


@tool
@handle_tool_errors(
    instructions={
        GoogleAPIError.BYTES_BILLED_LIMIT_EXCEEDED: (
            "Use `execute_bigquery_sql` with a WHERE clause "
            "to inspect a sample of the column's values"
        )
    }
)
def inspect_column_values(table_gcp_id: str, column_name: str) -> str:
    """Show actual distinct values in a column.

    FALLBACK tool to use when `search_dictionary_table()` fails.
    Useful for understanding data patterns and planning `WHERE` clauses.

    Args:
        table_gcp_id (str): Full BigQuery table reference
        column_name (str): Column name from `get_dataset_details()`

    Returns:
        str: JSON array of distinct values.
    """  # noqa: E501
    client = get_bigquery_client()

    sql_query = f"SELECT DISTINCT {column_name} FROM {table_gcp_id}"

    job_config = bq.QueryJobConfig(maximum_bytes_billed=LIMIT_INSPECTION_QUERY)
    query_job = client.query(sql_query, job_config=job_config)

    rows = query_job.result()
    results = [row.get(column_name) for row in rows]

    tool_output = ToolOutput(status="success", results=results).model_dump(exclude_none=True)
    return json.dumps(tool_output, ensure_ascii=False, default=str)


def get_tools() -> list[BaseTool]:
    """Return all available tools for Base dos Dados database interaction.

    This function provides a complete set of tools for discovering, exploring,
    and querying Brazilian public datasets through the Base dos Dados platform.

    Returns:
        list[BaseTool]: A list of LangChain tool functions in suggested usage order:
            - search_datasets: Find datasets using keywords
            - get_dataset_details: Get comprehensive dataset information
            - execute_bigquery_sql: Execute SQL queries against BigQuery tables
            - decode_table_values: Decode coded values using dictionary tables
            - inspect_column_values: Inspect actual column values as fallback
    """
    return [
        search_datasets,
        get_dataset_details,
        execute_bigquery_sql,
        decode_table_values,
        inspect_column_values,
    ]
