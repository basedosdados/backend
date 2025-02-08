#%% SQL
import os
import psycopg2
from psycopg2 import sql
import dotenv
dotenv.load_dotenv()

db_host = os.environ.get("POSTGRES_HOST")
db_name = os.environ.get("POSTGRES_DB")
db_user = os.environ.get("POSTGRES_USER")
db_password = os.environ.get("POSTGRES_PASSWORD")
db_port = os.environ.get("POSTGRES_PORT", 5432)  # Default port is 5432

db = psycopg2.connect(
	host=db_host,
	database=db_name,
	user=db_user,
	password=db_password,
	port=db_port
)
cursor = db.cursor()

def get_scheme():
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
		ct.gcp_dataset_id, ct.gcp_table_id,
		'-- ' || t.name || '
	' ||
		'CREATE TABLE ' || ct.gcp_dataset_id || ct.gcp_table_id || ' (
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
	out = cursor.execute(sql)
	breakpoint()
# %%

get_scheme()
