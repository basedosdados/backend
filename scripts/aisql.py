import os
import cachetools.func
import psycopg2
from psycopg2 import sql
import dotenv
from itertools import groupby
from operator import itemgetter

dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

db_host = os.environ["DB_HOST"]
db_name = os.environ["DB_NAME"]
db_user = os.environ["DB_USER"]
db_password = os.environ["DB_PASSWORD"]
db_port = os.environ.get("DB_PORT", 5432)

db = psycopg2.connect(
    host=db_host,
    database=db_name,
    user=db_user,
    password=db_password,
    port=db_port
)
cursor = db.cursor()

@cachetools.func.ttl_cache(ttl=60*60*24)
def get_schema():
    sql_query = """--sql
    WITH columnexpr AS (
    SELECT
        table_id,
        STRING_AGG(
            c.name || ' ' || bt.name ||
            ', -- Description: ' || COALESCE(c.description, 'No description') ||
            CASE WHEN c.measurement_unit IS NOT NULL THEN '; Unit: ' || c.measurement_unit ELSE '' END ||
            CASE WHEN c.observations IS NOT NULL THEN '; Notes: ' || c.observations ELSE '' END,
            '\n        ' ORDER BY c.order) :: TEXT AS col_expr
    FROM
        "column" c 
    INNER JOIN bigquery_type bt ON c.bigquery_type_id = bt.id
    GROUP BY table_id
    )

    SELECT
        ct.gcp_dataset_id, ct.gcp_table_id, dataset_id,
        '-- ' || t.name || '
CREATE TABLE ' || ct.gcp_dataset_id || '.' || ct.gcp_table_id || ' (
        ' ||  c.col_expr || '
        ) COMMENT = ''' || COALESCE(t.description, 'No description') || ''';' AS schema_sql
    FROM
        cloud_table ct 
        INNER JOIN "table" t ON t.id = ct.table_id
        INNER JOIN "columnexpr" c ON t.id = c.table_id
    ORDER BY t.slug;
    """
    cursor.execute(sql_query)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

@cachetools.func.ttl_cache(ttl=60*60*24)
def get_dataset_descriptions():
    sql_query = """
    SELECT id, name, description 
    FROM dataset
    """
    cursor.execute(sql_query)
    columns = [desc[0] for desc in cursor.description]
    out = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return {d['id']: d for d in out}
import io

def gen_full_dump(schema=None, datasets=None):
    schema = schema or get_schema(); datasets = datasets or get_dataset_descriptions()

    schema = [t for t in schema if t['dataset_id'] in datasets] # fitler tables by ds

    sorted_schema = sorted(schema, key=itemgetter('dataset_id'))
    grouped_schemas = groupby(sorted_schema, key=itemgetter('dataset_id'))

    output = io.StringIO()

    for dataset_id, tables in grouped_schemas:
        tables = list(tables)
        dataset_info = datasets[dataset_id]
        output.write(f"\n{'='*80}\n")
        output.write(f"Dataset: {dataset_info['name']}\n")
        output.write(f"Description: {dataset_info['description']}\n")
        output.write(f"{'='*80}\n\n")
        for table in tables:
            output.write(table['schema_sql'])
            output.write('\n\n')
    return output.getvalue()

if __name__ == '__main__':
    print(gen_full_dump())
