# -*- coding: utf-8 -*-
import json
import os
from typing import Any, Literal, Optional

import httpx
from google.api_core import exceptions
from google.cloud import bigquery as bq
from langchain_core.tools import tool
from pydantic import BaseModel

SEARCH_URL = "https://backend.basedosdados.org/search/"
GRAPHQL_URL = "https://backend.basedosdados.org/graphql"

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


class Column(BaseModel):
    name: str
    type: str
    description: Optional[str]


class Table(BaseModel):
    id: str
    gcp_id: Optional[str]
    name: str
    slug: Optional[str]
    description: Optional[str]
    columns: list[Column]


class DatasetOverview(BaseModel):
    id: str
    name: str
    slug: Optional[str]
    description: Optional[str]
    tags: list[str]
    themes: list[str]
    organizations: list[str]


class Dataset(DatasetOverview):
    tables: list[Table]


class ToolOutput(BaseModel):
    status: Literal["success", "error"]
    results: Optional[Any] = None
    error_details: Optional[dict[str, Any]] = None


client = bq.Client(project=os.environ["QUERY_PROJECT_ID"])


@tool
def search_datasets(query: str) -> str:
    """Search for datasets in the Base dos Dados (BD) database using KEYWORDS ONLY.

    IMPORTANT: This search uses Elasticsearch - use individual KEYWORDS, NOT full sentences.
    Use this as the FIRST STEP when exploring data. If no relevant datasets are found,
    try searching again with different or more specific keywords.

    Args:
        query (str): Individual keywords (2-3 words max). The search engine works best with single keywords. Use:
            - Single topic words: "educação", "saúde", "economia", "emprego", "população", "criminalidade"
            - Geographic keywords: "municipal", "estado", "brasil", "sao paulo", "rio"
            - Dataset names: "censo", "pnad", "rais", "caged"
            - Organization acronyms: "ibge", "inep", "anvisa", "tse"

            AVOID full sentences like "Brazilian population data by municipality"
            INSTEAD use: "censo" or "ibge" or "populacao" or "municipio"

    Returns:
        str: JSON array of dataset overviews. If empty array `[]` or irrelevant results:
            - Try different keywords (synonyms, abbreviations)
            - Use more specific terms or broader terms
            - Try organization names or data source acronyms (caged, ibge, rais, censo, etc.)

    Search Strategy:
        1. Use portuguese keywords: "educacao" instead of "education"
        2. Use government agency acronyms: "ibge", "inep", "anvisa"
        3. Use dataset-specific terms: "censo", "rais", "pnad", "caged"
        4. Search by geographic level: "municipio", "estado", "regiao"

    Next steps after using this tool:
        1. If no results or irrelevant results: Try different keywords and search again
        2. If good results: Review datasets to identify the most relevant ones
        3. Use `get_dataset_details()` with the dataset `id` to explore structure
        4. Look for datasets from reputable organizations (IBGE and other government agencies)

    Example successful searches:
        - "censo" → finds census datasets
        - "educacao" → finds education data
        - "emprego" → finds labour data
        - "saude municipio" → finds municipal health data
        - "ibge" → finds all IBGE datasets
        - "eleicoes" → finds election datasets
    """  # noqa: E501
    try:
        with httpx.Client() as client:
            response = client.get(
                url=SEARCH_URL,
                params={"q": query, "page_size": 10},
                timeout=httpx.Timeout(5.0, read=60.0),
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
    except Exception as e:
        tool_output = ToolOutput(
            status="error", error_details={"message": f"Error searching datasets:\n{e}"}
        ).model_dump(exclude_none=True)

    return json.dumps(tool_output, ensure_ascii=False, indent=2)


@tool
def get_dataset_details(dataset_id: str) -> str:
    """Get comprehensive details about a specific dataset including all tables and columns.

    This tool provides the complete structure of a dataset, showing all available tables,
    their columns, data types, and BigQuery identifiers. Use this AFTER `search_datasets()`
    to understand what data is available before writing SQL queries.

    Args:
        dataset_id (str): The unique dataset ID obtained from `search_datasets()`.
            This is typically a UUID-like string, not the human-readable name.

    Returns:
        str: JSON object with complete dataset information including:
            - Basic metadata (name, description, tags, themes, organizations)
            - tables: Array of all tables in the dataset with:
                - gcp_id: Full BigQuery table reference (`project.dataset.table`)
                - columns: All column names, types (STRING, INTEGER, DATE, etc.), and descriptions
                - Table descriptions explaining what each table contains

    Next steps after using this tool:
        1. Identify which table(s) contain the data you need
        2. Check column descriptions to understand what each field represents
        3. Note the column names and types for SQL query construction
        4. Use the `gcp_id` (BigQuery table reference) in your SQL queries
        5. Plan your SQL query using `execute_sql_query()`

    IMPORTANT:
        - The `gcp_id` field is the full BigQuery table reference you'll use in FROM clauses
        - Column types help you write correct SQL (STRING needs quotes, dates need DATE functions, etc.)
        - Some tables may be very large - consider using LIMIT in your queries
        - Look for key identifier columns (like municipality codes, dates, etc.) for filtering

    Example workflow:
        1. `search_datasets("IBGE")` → get dataset IDs
        2. `get_dataset_details("abc-123-def")` → explore tables structure
        3. `execute_sql_query("SELECT * FROM `basedosdados.br_ibge_censo.municipio` LIMIT 10")`
    """  # noqa: E501
    try:
        with httpx.Client() as client:
            response = client.post(
                url=GRAPHQL_URL,
                json={
                    "query": DATASET_DETAILS_QUERY,
                    "variables": {"id": dataset_id},
                },
                timeout=httpx.Timeout(5.0, read=60.0),
            )
            response.raise_for_status()
            data: dict[str, dict[str, dict]] = response.json()

        dataset_edges = data.get("data").get("allDataset", {}).get("edges", [])

        if not dataset_edges:
            return f"Dataset {dataset_id} not found"

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
    except Exception as e:
        tool_output = ToolOutput(
            status="error", error_details={"message": f"Error fetching dataset details:\n{e}"}
        ).model_dump(exclude_none=True)

    return json.dumps(tool_output, ensure_ascii=False, indent=2)


@tool
def execute_bigquery_sql(sql_query: str) -> str:
    """Execute a SQL query against BigQuery tables from the Base dos Dados database.

    This tool runs your SQL query and returns the results. It includes safety checks
    to prevent expensive queries (>20GB processing limit). Use this as the FINAL STEP
    after identifying the right datasets and understanding their structure.

    Args:
        sql_query (str): Standard SQL query using BigQuery syntax. Must reference
            tables using their full `gcp_id` from get_dataset_details().

            SQL Best Practices:
            - Use fully qualified table names: `project.dataset.table`
            - Select only needed columns, avoid SELECT *
            - Add LIMIT clause for exploration: LIMIT 10, LIMIT 100
            - Filter early with WHERE clauses to reduce data processing
            - Order results by relevant columns to present the most significant results first.
            - Never use DDL (e.g, `CREATE`, `ALTER`, `DROP`) or DML (e.g., `INSERT`, `UPDATE`, `DELETE`) commands
            - Use appropriate data types in comparisons

    Returns:
        str: Query results as JSON array of objects, where each object represents a row. Special cases:
            - Empty results: Returns "[]"
            - Query too large: Returns error with processing size details
            - SQL errors: Returns error message with details for debugging

    Safety Features:
        - Dry run validation before execution
        - 20GB processing limit to prevent expensive queries

    Next steps after using this tool:
        1. If results are empty, check your filters and table names
        2. If you get size limit errors, add more specific WHERE conditions
        3. For large result sets, consider using LIMIT or aggregation
        4. Analyze results and refine query if needed
        5. Format results for final presentation

    Common SQL patterns for Base dos Dados:
        ```sql
        -- Basic exploration
        SELECT * FROM `basedosdados.br_inep_ideb.municipio` LIMIT 10

        -- Filtered by geography
        SELECT * FROM `basedosdados.br_inep_ideb.municipio`
        WHERE sigla_uf = 'SP' LIMIT 100

        -- Aggregation by region
        SELECT sigla_uf, COUNT(*)
        FROM `basedosdados.br_inep_ideb.municipio`
        GROUP BY sigla_uf

        -- Time series data
        SELECT ano, AVG(ideb) FROM `basedosdados.br_inep_ideb.municipio`
        WHERE ano BETWEEN 2010 AND 2020
        GROUP BY ano
        ORDER BY ano
        ```

    Troubleshooting:
        - "Not found" → Check `gcp_id` from `get_dataset_details()`
        - "Unrecognized name" → Verify column names match table structure from `get_dataset_details()`
        - "Query too large" → Add WHERE filters or select fewer columns
        - "Syntax error" → Check GoogleSQL syntax
    """  # noqa: E501
    try:
        job_config = bq.QueryJobConfig(dry_run=True, use_query_cache=False)
        query_job = client.query(sql_query, job_config=job_config)

        limit_bytes = 20e9  # 20GB limit for queries

        if query_job.total_bytes_processed > limit_bytes:
            tool_output = ToolOutput(
                status="error",
                error_details={
                    "type": "QueryTooLarge",
                    "limit_bytes": limit_bytes,
                    "total_processed_bytes": query_job.total_bytes_processed,
                    "message": (
                        "Query aborted: Data processed exceeds the 20GB per-query limit. "
                        "Consider optimizing by adding filters, selecting fewer columns, "
                        "or using a LIMIT clause before retrying."
                    ),
                },
            )
            return tool_output.model_dump_json(indent=2, exclude_none=True)

        rows = client.query(sql_query).result()

        results = [dict(row) for row in rows]

        tool_output = ToolOutput(status="success", results=results).model_dump(exclude_none=True)
    except Exception as e:
        tool_output = ToolOutput(
            status="error", error_details={"message": f"SQL query execution failed:\n{e}"}
        ).model_dump(exclude_none=True)

    return json.dumps(tool_output, ensure_ascii=False)


@tool
def inspect_column_values(table_gcp_id: str, column_name: str, limit: int = 100) -> str:
    """Inspect the actual values in a specific column to understand data content and patterns.

    Use this tool as a FALLBACK when `search_dictionary_table()` fails or returns no results.
    Always try `search_dictionary_table()` FIRST before using this tool, as dictionary tables
    provide more meaningful information about coded values.

    Args:
        table_gcp_id (str): Full BigQuery table reference from get_table_details() (project.dataset.table)
        column_name (str): Exact column name as shown in get_table_details()
        limit (int, optional): Maximum number of distinct values to return (default: 100)
            Use smaller limits (10-20) for initial exploration, larger for comprehensive views

    Returns:
        str: JSON array of distinct values found in the column, sorted by frequency.
            - Shows actual data patterns (encoded IDs, abbreviations, etc.)
            - Reveals if values are numeric codes that need dictionary decoding
            - Helps identify filtering options and data quality issues

    Use this tool when:
        - Planning WHERE clauses to see available filter values
        - Column values look like codes (1, 2, 3 or 'A', 'B', 'C') that might need decoding
        - Getting "no results" from queries and need to verify correct values
        - Understanding data patterns before analysis
        - Checking for NULL values or data quality issues

    Next steps after using this tool:
        1. If values look like codes → Use search_dictionary_table() to find meanings
        2. If values are clear → Use them directly in WHERE clauses
        3. If unexpected values → Investigate data quality or documentation
        4. Plan your main analysis query with correct filter values

    Example workflow:
        1. get_table_details("table-id") → see columns
        2. inspect_column_values("project.dataset.table", "tipo_escola") → see actual values
        3. If returns [1,2,3,4] → search dictionary for meanings
        4. execute_sql_query with proper filters based on real values

    Common patterns in Brazilian data:
        - Estado codes: 11, 12, 13 (need IBGE state dictionary)
        - Municipality codes: 3550308 (São Paulo city IBGE code)
        - Category codes: 1,2,3,4 (often need dataset dictionary)
        - Yes/No: 0/1 or S/N depending on dataset
    """  # noqa: E501
    sql_query = f"SELECT DISTINCT {column_name} FROM {table_gcp_id} LIMIT {limit}"

    try:
        job_config = bq.QueryJobConfig(dry_run=True, use_query_cache=False)
        query_job = client.query(sql_query, job_config=job_config)

        limit_bytes = 5e9  # 5GB limit for inspection queries

        if query_job.total_bytes_processed and query_job.total_bytes_processed > limit_bytes:
            bytes_processed_gb = query_job.total_bytes_processed / 1e9
            return ToolOutput(
                status="error",
                error_details={
                    "status": "error",
                    "type": "QueryTooLarge",
                    "limit_bytes": limit_bytes,
                    "total_processed_bytes": query_job.total_bytes_processed,
                    "message": (
                        f"Column inspection exceeds the 5GB per-query "
                        f"limit for inspection({bytes_processed_gb:.1f} GB). "
                        "Try a smaller limit or add WHERE filters to reduce data size."
                    ),
                },
            ).model_dump_json(indent=2, exclude_none=True)

        rows = client.query(sql_query).result()

        results = [row.get(column_name) for row in rows]

        tool_output = ToolOutput(status="success", results=results).model_dump(exclude_none=True)
    except Exception as e:
        tool_output = ToolOutput(
            status="error", error_details={"message": f"Failed to inspect colum values:\n{e}"}
        ).model_dump(exclude_none=True)

    return json.dumps(tool_output, ensure_ascii=False)


@tool
def search_dictionary_table(dataset_gcp_id: str, table_name: str, column_name: str) -> str:
    """Look up the meaning of coded values in a column using the dataset's dictionary table

    **ALWAYS USE THIS TOOL FIRST** when you need to understand column values before `inspect_column_values()`.
    Many Base dos Dados datasets use coded values or abbreviations for storage efficiency.
    This tool provides the authoritative meanings of these codes.

    Args:
        dataset_gcp_id (str): Dataset portion of BigQuery reference (project.dataset_name)
            - Extract from table gcp_id: if table is "basedosdados.br_ibge_censo.municipio"
            - Use dataset_gcp_id: "basedosdados.br_ibge_censo"
        table_name (str): Just the table name (not full gcp_id)
            - Extract from gcp_id: if "basedosdados.br_ibge_censo.municipio"
            - Use table_name: "municipio"
        column_name (str): Exact column name that contains encoded values

    Returns:
        str: JSON array of dictionary mappings with structure:
            - chave: The encoded value found in your data (1, 2, 'A', 'B', etc.)
            - valor: Human-readable meaning/description

        If no mappings found, returns guidance on alternative approaches.

    Next steps after using this tool:
        1. Match the returned 'chave' values with codes in your data
        2. Use JOIN with dictionary table for readable results:
           ```sql
           SELECT t.*, d.valor as decoded_column
           FROM `project.dataset.table` t
           LEFT JOIN `project.dataset.dicionario` d
           ON t.encoded_column = d.chave
           AND d.id_tabela = 'table_name'
           AND d.nome_coluna = 'column_name'
           ```
        3. Or use the mappings to understand what codes mean for filtering

    Example usage:
        # After inspect_column_values shows tipo_escola has values [1,2,3,4]:
        search_dictionary_table("basedosdados.br_inep_censo_escolar", "escola", "tipo_escola")

        # Result might show: 1='Pública', 2='Privada', 3='Federal', 4='Municipal'

        # Then use in queries:
        SELECT tipo_escola, COUNT(*) FROM `basedosdados.br_inep_censo_escolar.escola`
        WHERE tipo_escola IN (1, 2)  -- Now you know 1=Pública, 2=Privada
        GROUP BY tipo_escola

    Common encoded column types in Brazilian data:
        - Geographic codes: estado, municipio (IBGE codes)
        - Category codes: tipo_*, categoria_*, situacao_*
        - Status codes: ativo, situacao, condicao
        - Classification codes: nivel_*, grau_*, classe_*

    If no dictionary found:
        - Dataset might not have encoded values
        - Values might be in separate reference tables
        - Try common directory datasets like br_bd_diretorios_brasil
    """  # noqa: E501

    # Build the specific query for this table/column combination
    dict_table_id = f"{dataset_gcp_id}.dicionario"

    search_query = f"""
        SELECT nome_coluna, chave, valor
        FROM {dict_table_id}
        WHERE id_tabela = '{table_name}'
    """

    if column_name is not None:
        search_query += f"AND nome_coluna = '{column_name}'"

    search_query += "ORDER BY nome_coluna, chave"

    try:
        job_config = bq.QueryJobConfig(dry_run=True, use_query_cache=False)
        query_job = client.query(search_query, job_config=job_config)

        limit_bytes = 1e9  # 1GB limit for dictionary queries

        if query_job.total_bytes_processed > limit_bytes:
            return ToolOutput(
                status="error",
                error_details={
                    "type": "QueryTooLarge",
                    "limit_bytes": limit_bytes,
                    "total_processed_bytes": query_job.total_bytes_processed,
                    "message": (
                        "Dictionary table is unexpectedly large. "
                        "This might not be the right approach. "
                        "Check if this dataset actually uses "
                        "encoded values or try a different table."
                    ),
                },
            ).model_dump_json(indent=2, exclude_none=True)

        rows = client.query(search_query).result()
        results = [dict(row) for row in rows]
        tool_output = ToolOutput(status="success", results=results).model_dump(exclude_none=True)
    except exceptions.NotFound:
        return ToolOutput(
            status="error",
            error_details={
                "type": "TableNotFound",
                "message": (
                    f"Dictionary table not found for dataset {dataset_gcp_id}. "
                    "This indicates this dataset does not contain a dicionary table. "
                    "Consider using the `inspect_column_values` tool to inspect column values."
                ),
            },
        ).model_dump_json(indent=2, exclude_none=True)
    except Exception as e:
        tool_output = ToolOutput(
            status="error", error_details={"message": f"Failed to search dictionary table:\n{e}"}
        ).model_dump(exclude_none=True)

    return json.dumps(tool_output, ensure_ascii=False)
