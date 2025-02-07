#%% SQL
sql = """--sql
with columnexpr as (
select
	table_id,
	STRING_AGG(
        c.name || ' ' || bt.name ||
        ', -- Description: ' || coalesce(c.description,
	'No description') ||
        case
		when c.measurement_unit is not null then '; Unit: ' || c.measurement_unit
		else ''
	end ||
        case
		when c.observations is not null then '; Notes: ' || c.observations
		else ''
	end,
	'
    ' order by c.order) :: TEXT as col_expr
	from
		"column" c inner join bigquery_type bt on c.bigquery_type_id = bt.id
	group by table_id
)

select
	 ct.gcp_dataset_id, ct.gcp_table_id,
	'-- ' || t.name || '
' ||
    'CREATE TABLE ' || ct.gcp_dataset_id || ct.gcp_table_id || ' (
    ' ||  c.col_expr ||
    '
) COMMENT = ''' || coalesce(t.description, 'No description') || ''';' as schema_sql
from
	"table" t
inner join cloud_table ct on
	t.id = ct.table_id
inner join "columnexpr" c on
	t.id = c.table_id
order by
	t.slug;
"""

