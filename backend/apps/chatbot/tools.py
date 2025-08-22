# -*- coding: utf-8 -*-
import json
import os
from typing import Optional

import httpx
from google.cloud import bigquery as bq
from langchain_core.tools import tool
from pydantic import BaseModel

SEARCH_URL = "https://backend.basedosdados.org/search/"
GRAPHQL_URL = "https://backend.basedosdados.org/graphql"

DATASET_OVERVIEW_QUERY = """
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


client = bq.Client(project=os.environ["QUERY_PROJECT_ID"])


@tool
def search_datasets(query: str) -> str:
    """Search for datasets in the Base dos Dados (BD) catalog using KEYWORDS ONLY.

    IMPORTANT: This search uses Elasticsearch - use individual KEYWORDS, NOT full sentences.
    Use this as the FIRST STEP when exploring data. If no relevant datasets are found,
    try searching again with different or more specific keywords.

    Args:
        query (str): Individual keywords or short phrases (2-3 words max). The search engine
            works best with single keywords. Use:
            - Single topic words: "education", "health", "economy", "population", "crime"
            - Geographic keywords: "municipal", "estado", "brasil", "sao_paulo", "rio"
            - Data type keywords: "censo", "pnad", "rais", "sinasc", "datasus"
            - Organization keywords: "ibge", "inep", "ans", "bacen", "tse"

            AVOID full sentences like "Brazilian population data by municipality"
            INSTEAD use: "populacao" or "municipio" or "ibge censo"

    Returns:
        str: JSON array of dataset overviews. If empty array [] or irrelevant results:
            - Try different keywords (synonyms, Portuguese terms, abbreviations)
            - Use more specific terms or broader terms
            - Try organization names or data source acronyms

    Search Strategy - If initial search fails:
        1. Try Portuguese keywords: "educacao" instead of "education"
        2. Use government agency acronyms: "ibge", "inep", "anvisa", "ans"
        3. Try broader terms: "social" instead of specific indicators
        4. Use dataset-specific terms: "pnad", "censo", "rais", "caged"
        5. Search by geographic level: "municipio", "estado", "regiao"

    Next steps after using this tool:
        1. If no results or irrelevant results → Try different keywords and search again
        2. If good results → Review datasets to identify the most relevant ones
        3. Use get_dataset_details() with the dataset 'id' to explore structure
        4. Look for datasets from reputable organizations (IBGE, government agencies)

    Example successful searches:
        - "censo" → finds census datasets
        - "educacao" → finds education data
        - "saude municipio" → finds municipal health data
        - "ibge" → finds all IBGE datasets
        - "eleicoes" → finds election datasets
    """
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

        return json.dumps(overviews, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error searching datasets:\n{e}"


@tool
def get_dataset_details(dataset_id: str) -> str:
    """Get comprehensive details about a specific dataset including all tables and columns.

    This tool provides the complete structure of a dataset, showing all available tables,
    their columns, data types, and BigQuery identifiers. Use this AFTER search_datasets()
    to understand what data is available before writing SQL queries.

    Args:
        dataset_id (str): The unique dataset ID obtained from search_datasets().
            This is typically a UUID-like string, not the human-readable name.

    Returns:
        str: JSON object with complete dataset information including:
            - Basic metadata (name, description, themes, organizations)
            - tables: Array of all tables in the dataset with:
                - gcp_id: Full BigQuery table reference (project.dataset.table)
                - columns: All column names, types (STRING, INTEGER, DATE, etc.), and descriptions
                - Table descriptions explaining what each table contains

    Next steps after using this tool:
        1. Identify which table(s) contain the data you need
        2. Note the column names and types for SQL query construction
        3. Use the gcp_id (BigQuery table reference) in your SQL queries
        4. Check column descriptions to understand what each field represents
        5. Plan your SQL query using execute_sql_query()

    Important notes:
        - The 'gcp_id' field is the full BigQuery table reference you'll use in FROM clauses
        - Column types help you write correct SQL (STRING needs quotes, dates need DATE functions)
        - Some tables may be very large - consider using LIMIT in your queries
        - Look for key identifier columns (like municipality codes, dates) for filtering

    Example workflow:
        1. search_datasets("IBGE census") → get dataset IDs
        2. get_dataset_details("abc-123-def") → explore table structure
        3. execute_sql_query("SELECT * FROM `basedosdados.br_ibge_censo.municipio` LIMIT 10")
    """
    try:
        with httpx.Client() as client:
            response = client.post(
                url=GRAPHQL_URL,
                json={
                    "query": DATASET_OVERVIEW_QUERY,
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

        return json.dumps(dataset, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error fetching dataset details:\n{e}"


@tool
def execute_sql_query(sql_query: str) -> str:
    """Execute a SQL query against BigQuery tables from the Base dos Dados catalog.

    This tool runs your SQL query and returns the results. It includes safety checks
    to prevent expensive queries (>10GB processing limit). Use this as the FINAL STEP
    after identifying the right datasets and understanding their structure.

    Args:
        sql_query (str): Standard SQL query using BigQuery syntax. Must reference
            tables using their full gcp_id from get_dataset_details().

            SQL Best Practices:
            - Use backticks around table names: `project.dataset.table`
            - Add LIMIT clause for exploration: LIMIT 10, LIMIT 100
            - Filter early with WHERE clauses to reduce data processing
            - Select only needed columns, avoid SELECT *
            - Use appropriate data types in comparisons

    Returns:
        str: Query results as JSON array of objects, where each object represents a row.
            Special cases:
            - Empty results: Returns "[]"
            - Query too large: Returns error with processing size details
            - SQL errors: Returns error message with details for debugging

    Safety Features:
        - Dry run validation before execution
        - 10GB processing limit to prevent expensive queries
        - Automatic query optimization suggestions if limit exceeded

    Next steps after using this tool:
        1. If results are empty, check your filters and table names
        2. If you get size limit errors, add more specific WHERE conditions
        3. For large result sets, consider using LIMIT or aggregation
        4. Analyze results and refine query if needed
        5. Format or visualize results for final presentation

    Common SQL patterns for Base dos Dados:
        ```sql
        -- Basic exploration
        SELECT * FROM `basedosdados.br_ibge_censo_2010.municipio` LIMIT 10

        -- Filtered by geography
        SELECT * FROM `table` WHERE sigla_uf = 'SP' LIMIT 100

        -- Aggregation by region
        SELECT sigla_uf, COUNT(*) FROM `table` GROUP BY sigla_uf

        -- Time series data
        SELECT ano, SUM(valor) FROM `table`
        WHERE ano BETWEEN 2010 AND 2020 GROUP BY ano ORDER BY ano
        ```

    Troubleshooting:
        - "Table not found" → Check gcp_id from get_dataset_details()
        - "Column not found" → Verify column names match dataset structure
        - "Query too large" → Add WHERE filters or select fewer columns
        - "Syntax error" → Check BigQuery SQL syntax and table backticks
    """
    try:
        job_config = bq.QueryJobConfig(dry_run=True, use_query_cache=False)
        query_job = client.query(sql_query, job_config=job_config)

        limit_bytes = 10e9  # 10GB

        if query_job.total_bytes_processed > limit_bytes:
            return json.dumps(
                {
                    "status": "error",
                    "error_type": "query_too_large",
                    "total_processed_bytes": query_job.total_bytes_processed,
                    "limit_bytes": limit_bytes,
                    "message": (
                        "Query aborted: Data processed exceeds the 10GB per-query limit. "
                        "Consider optimizing by adding filters, selecting fewer columns, "
                        "or using a LIMIT clause before retrying."
                    ),
                },
                indent=2,
            )

        rows = client.query(sql_query).result()

        results = [dict(row) for row in rows]

        if results:
            return json.dumps(results, ensure_ascii=False, default=str)
        return "[]"
    except Exception as e:
        return f"SQL query execution failed:\n{e}"


@tool
def inspect_column_values(table_gcp_id: str, column_name: str, limit: int = 100) -> str:
    """Inspect the actual values present in a specific column to understand data patterns and encoding.

    This tool helps you understand what values actually exist in a column before writing filters
    or joins. Essential for avoiding "value not found" errors and discovering encoded values
    that need dictionary lookups.

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
    sql_query = f"SELECT DISTINCT({column_name}) FROM `{table_gcp_id}` LIMIT {limit}"

    try:
        # Check query size first
        job_config = bq.QueryJobConfig(dry_run=True, use_query_cache=False)
        query_job = client.query(sql_query, job_config=job_config)

        limit_bytes = 5e9  # 5GB limit for inspection queries
        if query_job.total_bytes_processed and query_job.total_bytes_processed > limit_bytes:
            bytes_processed_gb = query_job.total_bytes_processed / 1e9
            return json.dumps(
                {
                    "status": "error",
                    "error_type": "query_too_large",
                    "total_processed_bytes": query_job.total_bytes_processed,
                    "limit_bytes": limit_bytes,
                    "message": (
                        f"Column inspection would process {bytes_processed_gb:.1f} GB. "
                        "Try a smaller limit or add WHERE filters to reduce data size."
                    ),
                },
                indent=2,
            )

        rows = client.query(sql_query).result()
        results = [dict(row) for row in rows]
        if results:
            return json.dumps(results, ensure_ascii=False, default=str)
        return "[]"
    except Exception as e:
        return f"Failed to inspect colum values:\n{e}"


@tool
def search_dictionary_table(dataset_gcp_id: str, table_name: str, column_name: str) -> str:
    """Look up the meaning of encoded values using the dataset's dictionary table.

    Many Brazilian datasets use numeric codes or abbreviations for storage efficiency.
    The 'dicionario' table provides mappings from encoded values (chave) to human-readable
    meanings (valor). Use this after inspect_column_values() reveals coded values.

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
    """
    try:
        # Build the specific query for this table/column combination
        dict_table_id = f"{dataset_gcp_id}.dicionario"

        search_query = f"""
        SELECT chave, valor
        FROM `{dict_table_id}`
        WHERE id_tabela = '{table_name}'
        AND nome_coluna = '{column_name}'
        ORDER BY chave
        """

        # Check if query is reasonable size
        job_config = bq.QueryJobConfig(dry_run=True, use_query_cache=False)
        query_job = client.query(search_query, job_config=job_config)

        # Dictionary queries should be small, but let's be safe
        if query_job.total_bytes_processed > 1e9:  # 1GB limit
            return json.dumps(
                {
                    "status": "error",
                    "message": (
                        "Dictionary table is unexpectedly large. "
                        "This might not be the right approach."
                    ),
                    "suggestion": (
                        "Check if this dataset actually uses "
                        "encoded values or try a different table."
                    ),
                }
            )

        rows = client.query(search_query).result()
        results = [dict(row) for row in rows]

        if results:
            return json.dumps(results, ensure_ascii=False, default=str)
        else:
            # Try to see if dictionary table exists and what it contains
            fallback_query = f"""
            SELECT DISTINCT id_tabela, nome_coluna
            FROM `{dict_table_id}`
            WHERE id_tabela LIKE '%{table_name}%' OR nome_coluna LIKE '%{column_name}%'
            LIMIT 20
            """

            try:
                fallback_rows = client.query(fallback_query).result()
                similar_entries = [dict(row) for row in fallback_rows]

                return json.dumps(
                    {
                        "status": "no_exact_match",
                        "message": (
                            f"No dictionary entries found for table='{table_name}', "
                            f"column='{column_name}'"
                        ),
                        "similar_entries": similar_entries,
                        "suggestion": (
                            "Check if table_name or column_name needs "
                            "adjustment based on similar entries above."
                        ),
                    },
                    indent=2,
                )

            except Exception:
                return json.dumps(
                    {
                        "status": "no_dictionary",
                        "message": f"No dictionary table found in {dataset_gcp_id}",
                        "suggestion": (
                            "This dataset might not use encoded values, "
                            "or dictionary might be in a different location."
                        ),
                    },
                    indent=2,
                )

    except Exception as e:
        return f"Failed to search dictionary table:\n{e}"
