# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from django.core.management import call_command
from google.api_core.exceptions import GoogleAPICallError
from google.cloud.bigquery import Table as GBQTable
from huey import crontab
from huey.contrib.djhuey import periodic_task
from loguru import logger
from pandas import read_gbq
from requests import get

from bd_api.apps.api.v1.models import Dataset, RawDataSource, Table
from bd_api.custom.client import Messenger, get_gbq_client, get_gcs_client
from bd_api.utils import production_task

logger = logger.bind(module="api.v1")


@periodic_task(crontab(day_of_week="1-6", hour="5", minute="0"))
@production_task
def update_search_index_task():
    call_command("update_index", batchsize=100)


@periodic_task(crontab(day_of_week="0", hour="5", minute="0"))
@production_task
def rebuild_search_index_task():
    call_command("rebuild_index", interactive=False, batchsize=100)


@periodic_task(crontab(day_of_week="1-5", hour="6", minute="0"))
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
            except Exception as exc:
                logger.warning(exc)

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
            except Exception as exc:
                logger.warning(exc)

    bq_client = get_gbq_client()
    cs_client = get_gcs_client()
    cs_bucket = cs_client.get_bucket("basedosdados")

    messenger = Messenger("Verifique os metadados dos conjuntos:")

    if not table_pks:
        tables = (
            Table.objects
            .exclude(status__slug__in=["under_review"])
            .exclude(dataset__status__slug__in=["under_review"])
            .order_by("updated_at")
            .all()
        )  # fmt: skip
    else:
        tables = (
            Table.objects.filter(pk__in=table_pks)
            .exclude(status__slug__in=["under_review"])
            .exclude(dataset__status__slug__in=["under_review"])
            .order_by("updated_at")
            .all()
        )

    for table in tables:
        if messenger.is_full:
            break
        if not table.gbq_slug:
            continue
        try:
            bq_table = bq_client.get_table(table.gbq_slug)
            table.number_rows = get_number_of_rows(table, bq_table)
            table.number_columns = get_number_of_columns(table, bq_table)
            table.uncompressed_file_size = get_uncompressed_file_size(table, bq_table)
            table.save()
            logger.info(f"{table}")
        except Exception as exc:
            if isinstance(exc, GoogleAPICallError):
                exc = exc.response.json()["error"]
                exc = exc["errors"][0]["message"]
            messenger.append(table, exc)
            logger.warning(f"{table}: {exc}")

    messenger.send()


@periodic_task(crontab(day_of_week="1-5", hour="7", minute="0"))
@production_task
def update_page_views_task(backfill: bool = False):
    if backfill:
        event_table = "events_*"
    else:
        yesterday = datetime.now() - timedelta(1)
        yesterday = yesterday.strftime("%Y%m%d")
        event_table = f"events_{yesterday}"

    query = f"""
        select
            count(1) page_views
            , regexp_extract(param.value.string_value, r'table=([a-z0-9-]{{36}})') table_id
            , regexp_extract(param.value.string_value, r'dataset\/([a-z0-9-]{{36}})') dataset_id
        from `basedosdados.analytics_295884852.{event_table}` event
            join unnest(event_params) param
        where
            true
            and event_name = 'page_view'
            and param.key = 'page_location'
            and param.value.string_value like '%/dataset/%'
        group by
            table_id,
            dataset_id
        having
            true
            and table_id is not null
            and dataset_id is not null
    """  # noqa: W605
    metadata = read_gbq(query)

    if backfill:
        for table_id in metadata["table_id"].unique():
            if table := Table.objects.filter(id=table_id).first():
                table.page_views = 0
                table.save()
        for dataset_id in metadata["dataset_id"].unique():
            if dataset := Dataset.objects.filter(id=dataset_id).first():
                dataset.page_views = 0
                dataset.save()

    for _, (page_views, table_id, dataset_id) in metadata.iterrows():
        if table := Table.objects.filter(id=table_id).first():
            table.page_views += page_views
            table.save()
        if dataset := Dataset.objects.filter(id=dataset_id).first():
            dataset.page_views += page_views
            dataset.save()


@periodic_task(crontab(day_of_week="1-5", hour="8", minute="0"))
@production_task
def check_links_task():
    messenger = Messenger("Revise os seguintes links:")
    for entity in RawDataSource.objects.filter(url__isnull=False).all():
        if messenger.is_full:
            break
        try:
            response = get(entity.url)
            response.raise_for_status()
        except Exception as exc:
            messenger.append(entity, exc)
    messenger.send()
