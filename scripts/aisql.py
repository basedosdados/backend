#%% SQL
import os
import psycopg2
from psycopg2 import sql
import dotenv
from collections import defaultdict
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

def get_schema():
    sql = """--sql
    WITH columnexpr AS (
    SELECT
        table_id,
        STRING_AGG(
            c.name || ' ' || bt.name ||
            ', -- Description: ' || COALESCE(c.description,
        'No description') ||
            CASE
            WHEN c.measurement_unit IS NOT NULL THEN '; Unit: ' || c.measurement_unit
            ELSE ''
        END ||
            CASE
            WHEN c.observations IS NOT NULL THEN '; Notes: ' || c.observations
            ELSE ''
        END,
        '
        ' ORDER BY c.order) :: TEXT AS col_expr
        FROM
            "column" c INNER JOIN bigquery_type bt ON c.bigquery_type_id = bt.id
        GROUP BY table_id
    )

    SELECT
        ct.gcp_dataset_id, ct.gcp_table_id, dataset_id,
        '-- ' || t.name || '
CREATE TABLE ' || ct.gcp_dataset_id || '.' || ct.gcp_table_id || ' (
        ' ||  c.col_expr ||
        '
    ) COMMENT = ''' || COALESCE(t.description, 'No description') || ''';' AS schema_sql
    FROM
        "table" t
    INNER JOIN cloud_table ct ON
        t.id = ct.table_id
    INNER JOIN "columnexpr" c ON
        t.id = c.table_id
    ORDER BY
        t.slug;
    """
    cursor.execute(sql)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def get_dataset_descriptions():
    sql = """--sql
    SELECT id, name, description 
    FROM dataset
    """
    cursor.execute(sql)
    columns = [desc[0] for desc in cursor.description]
    out =  [dict(zip(columns, row)) for row in cursor.fetchall()]
    return {d['id']: d for d in out}
#%%

schema = get_schema()
datasets = get_dataset_descriptions()

#%%

from itertools import groupby
from operator import itemgetter

# Sort schema by dataset_id first since groupby requires sorted input
sorted_schema = sorted(schema, key=itemgetter('dataset_id'))
grouped_schemas = groupby(sorted_schema, key=itemgetter('dataset_id'))
for dataset_id, tables in grouped_schemas:
    tables = list(tables) # iterator
    dataset_info = datasets[dataset_id]
    print(f"\n{'='*80}")
    print(f"Dataset: {dataset_info['name']}")
    print(f"Description: {dataset_info['description']}")
    print(f"{'='*80}\n")
    
    for table in tables:
        print(table['schema_sql'])
        print()

# %%
