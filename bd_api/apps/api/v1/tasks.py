# -*- coding: utf-8 -*-
from django.core.management import call_command
from google.api_core.exceptions import BadRequest, NotFound
from google.cloud.bigquery import Table as GBQTable
from huey import crontab
from huey.contrib.djhuey import periodic_task
from loguru import logger
from pandas import read_gbq

from bd_api.apps.api.v1.models import Table
from bd_api.custom.client import get_gbq_client, get_gcs_client, send_discord_message
from bd_api.utils import production_task

logger = logger.bind(module="api.v1")

header = (
    "Verifique a atualização de metadados "
    "via [grafana](https://grafana.basedosdados.org/dashboards) dos conjuntos"
)


@periodic_task(crontab(day_of_week="0", hour="3", minute="0"))
@production_task
def update_table_metadata_task(table_pks: list[str] = None):
    """Update the metadata of selected tables in the database"""

    def get_number_of_rows(table: Table, bq_table: GBQTable) -> int | None:
        """Get number of rows from big query"""

        if bq_table.num_rows:
            return bq_table.num_rows or None

        if bq_table.table_type == "VIEW":
            try:
                query = f"""
                    SELECT COUNT(1) AS n_rows
                    FROM `{table.gbq_slug}`
                """
                number_rows = read_gbq(query)
                number_rows = number_rows.loc[0, "n_rows"]
                return number_rows or None
            except Exception as e:
                logger.warning(e)

    def get_number_of_columns(table: Table, bq_table: GBQTable):
        """Get number of columns from big query"""

        return len(bq_table.schema or []) or None

    def get_uncompressed_file_size(table: Table, bq_table: GBQTable) -> int | None:
        """Get file size in bytes from big query or storage"""

        if bq_table.num_bytes:
            return bq_table.num_bytes

        if bq_table.table_type == "VIEW":
            try:
                file_size: int = 0
                for blob in cs_bucket.list_blobs(prefix=table.gcs_slug):
                    file_size += blob.size
                return file_size
            except Exception as e:
                logger.warning(e)

    bq_client = get_gbq_client()
    cs_client = get_gcs_client()
    cs_bucket = cs_client.get_bucket("basedosdados")

    if not table_pks:
        tables = Table.objects.all()
    else:
        tables = Table.objects.filter(pk__in=table_pks).all()

    msg = []
    for table in tables:
        if not table.gbq_slug:
            continue
        try:
            logger.info(f"{table}")
            bq_table = bq_client.get_table(table.gbq_slug)
            table.number_rows = get_number_of_rows(table, bq_table)
            table.number_columns = get_number_of_columns(table, bq_table)
            table.uncompressed_file_size = get_uncompressed_file_size(table, bq_table)
            table.save()
        except (BadRequest, NotFound, ValueError) as e:
            logger.warning(f"{table}: {e}")
            msg.append(str(table.dataset))
        except Exception as e:
            logger.error(f"{table}: {e}")
            msg.append(str(table.dataset))

    if msg:
        msg = set(msg)
        msg = list(msg)
        msg = sorted(msg)
        msg.insert(0, header)
        msg = "\n- ".join(msg)
        send_discord_message(msg)


@periodic_task(crontab(day_of_week="1-6", hour="5", minute="0"))
@production_task
def update_search_index_task():
    call_command("update_index", batchsize=100)


@periodic_task(crontab(day_of_week="0", hour="5", minute="0"))
@production_task
def rebuild_search_index_task():
    call_command("rebuild_index", interactive=False, batchsize=100)
