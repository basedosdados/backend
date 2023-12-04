# -*- coding: utf-8 -*-
from django.contrib.admin import ModelAdmin
from django.core.management import call_command
from django.db.models.query import QuerySet
from django.http import HttpRequest
from google.api_core.exceptions import BadRequest, NotFound
from google.cloud.bigquery import Client as GBQClient
from google.cloud.storage import Client as GCSClient
from huey import crontab
from huey.contrib.djhuey import periodic_task
from pandas import read_gbq

from bd_api.apps.api.v1.models import Table
from bd_api.custom.client import get_credentials
from bd_api.custom.logger import setup_task_logger
from bd_api.utils import prod_task

logger = setup_task_logger()


@prod_task
@periodic_task(crontab(day_of_week="0", hour="3", minute="0"))
def update_table_metadata_task(
    modeladmin: ModelAdmin = None,
    request: HttpRequest = None,
    queryset: QuerySet = None,
):
    """Update the metadata of selected tables in the database"""

    def get_number_of_rows(table, bq_table):
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

    def get_number_of_columns(table, bq_table):
        """Get number of columns from big query"""

        return len(bq_table.schema or [])

    def get_uncompressed_file_size(table, bq_table):
        """Get file size in bytes from big query or storage"""

        if bq_table.num_bytes:
            return bq_table.num_bytes

        if bq_table.table_type == "VIEW":
            try:
                file_size = 0
                for blob in bucket.list_blobs(prefix=table.gcs_slug):
                    file_size += blob.size
            except Exception as e:
                logger.warning(e)

    creds = get_credentials()
    bq_client = GBQClient(credentials=creds)
    cs_client = GCSClient(credentials=creds)

    bucket = cs_client.get_bucket("basedosdados")

    tables: list[Table] = []
    match str(modeladmin):
        case "v1.DatasetAdmin":
            tables = Table.objects.filter(
                dataset__in=queryset,
                source_bucket_name__isnull=False,
            )
        case "v1.TableAdmin":
            tables = queryset.filter(source_bucket_name__isnull=False)
        case _:
            tables = Table.objects.filter(source_bucket_name__isnull=False)

    for table in tables:
        try:
            bq_table = bq_client.get_table(table.gbq_slug)
            table.number_rows = get_number_of_rows(table, bq_table)
            table.number_columns = get_number_of_columns(table, bq_table)
            table.uncompressed_file_size = get_uncompressed_file_size(table, bq_table)
            table.save()
        except (BadRequest, NotFound, ValueError) as e:
            logger.warning(e)
        except Exception as e:
            logger.error(e)


@prod_task
@periodic_task(crontab(day_of_week="1-6", hour="5", minute="0"))
def update_search_index_task():
    call_command("update_index", batchsize=100, workers=4)


@prod_task
@periodic_task(crontab(day_of_week="0", hour="5", minute="0"))
def rebuild_search_index_task():
    call_command("rebuild_index", interactive=False, batchsize=100, workers=4)
