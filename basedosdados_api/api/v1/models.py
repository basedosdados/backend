# -*- coding: utf-8 -*-
from typing import Iterable, Optional
from uuid import uuid4

from django.db import models

from basedosdados_api.api.v1.utils import (
    check_kebab_case,
    check_snake_case,
)


class Area(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name_en = models.CharField(max_length=255)
    name_pt = models.CharField(max_length=255)

    def __str__(self):
        return str(self.slug)

    class Meta:
        db_table = "area"
        verbose_name = "Area"
        verbose_name_plural = "Areas"
        ordering = ["slug"]


class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    # Foreign
    # spatial_coverage_area = models.ForeignKey(...)
    area = models.ForeignKey(
        "Area", on_delete=models.CASCADE, related_name="organizations"
    )
    # Mandatory
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(unique=True)
    name_en = models.CharField(max_length=255)
    name_pt = models.CharField(max_length=255)
    # Optional
    website = models.URLField(blank=True, null=True)

    def __str__(self):
        return str(self.slug)

    class Meta:
        db_table = "organization"
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"
        ordering = ["slug"]


class Dataset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    organization = models.ForeignKey(
        "Organization", on_delete=models.CASCADE, related_name="datasets"
    )
    # license = models.ForeignKey(...)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(unique=True)
    name_en = models.CharField(max_length=255)
    name_pt = models.CharField(max_length=255)

    def __str__(self):
        return str(self.slug)

    class Meta:
        db_table = "dataset"
        verbose_name = "Dataset"
        verbose_name_plural = "Datasets"
        ordering = ["slug"]


class Table(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    dataset = models.ForeignKey(
        "Dataset", on_delete=models.CASCADE, related_name="tables"
    )
    # update_frequency = models.ForeignKey(...)
    # pipeline = models.ForeignKey(...)
    # license = models.ForeignKey(...)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(unique=True)
    name_en = models.CharField(max_length=255)
    name_pt = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    is_directory = models.BooleanField(default=False, blank=True, null=True)
    data_cleaned_description = models.TextField(blank=True, null=True)
    data_cleaned_code_url = models.URLField(blank=True, null=True)
    raw_data_url = models.URLField(blank=True, null=True)
    auxiliary_files_url = models.URLField(blank=True, null=True)
    architecture_url = models.URLField(blank=True, null=True)
    source_bucket_name = models.CharField(max_length=255, blank=True, null=True)
    uncompressed_file_size = models.BigIntegerField(blank=True, null=True)
    compressed_file_size = models.BigIntegerField(blank=True, null=True)
    number_of_rows = models.BigIntegerField(blank=True, null=True)

    def __str__(self):
        return str(self.slug)

    class Meta:
        db_table = "table"
        verbose_name = "Table"
        verbose_name_plural = "Tables"
        ordering = ["slug"]


class BigQueryTypes(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return str(self.name)

    class Meta:
        db_table = "bigquery_types"
        verbose_name = "BigQuery Type"
        verbose_name_plural = "BigQuery Types"
        ordering = ["name"]


class Column(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    table = models.ForeignKey("Table", on_delete=models.CASCADE, related_name="columns")
    bigquery_type = models.ForeignKey(
        "BigQueryTypes", on_delete=models.CASCADE, related_name="columns"
    )
    slug = models.SlugField(unique=True)
    name_en = models.CharField(max_length=255)
    name_pt = models.CharField(max_length=255)
    is_in_staging = models.BooleanField(default=True)
    is_partition = models.BooleanField(default=False)
    description = models.TextField(blank=True, null=True)
    coverage_by_dictionary = models.BooleanField(default=False, blank=True, null=True)
    measurement_unit = models.CharField(max_length=255, blank=True, null=True)
    has_sensitive_data = models.BooleanField(default=False, blank=True, null=True)
    observations = models.TextField(blank=True, null=True)

    def __str__(self):
        return str(self.slug)

    class Meta:
        db_table = "column"
        verbose_name = "Column"
        verbose_name_plural = "Columns"
        ordering = ["slug"]


class CloudTable(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    table = models.ForeignKey(
        "Table", on_delete=models.CASCADE, related_name="cloud_tables"
    )
    columns = models.ManyToManyField("Column", related_name="cloud_tables")
    gcp_project_id = models.CharField(max_length=255)
    gcp_dataset_id = models.CharField(max_length=255)
    gcp_table_id = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.gcp_project_id}.{self.gcp_dataset_id}.{self.gcp_table_id}"

    def clean(self) -> None:
        if not check_kebab_case(self.gcp_project_id):
            raise ValueError("gcp_project_id must be in kebab-case.")
        if not check_snake_case(self.gcp_dataset_id):
            raise ValueError("gcp_dataset_id must be in snake_case.")
        if not check_snake_case(self.gcp_table_id):
            raise ValueError("gcp_table_id must be in snake_case.")
        for column in self.columns.all():
            if column.table != self.table:
                raise ValueError(
                    f"Column {column} does not belong to table {self.table}."
                )
        return super().clean()

    def save(
        self,
        force_insert: bool = False,
        force_update: bool = False,
        using: Optional[str] = None,
        update_fields: Optional[Iterable[str]] = None,
    ) -> None:
        self.clean()
        return super().save(force_insert, force_update, using, update_fields)

    class Meta:
        db_table = "cloud_table"
        verbose_name = "Cloud Table"
        verbose_name_plural = "Cloud Tables"
        ordering = ["id"]


class RawDataSource(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    dataset = models.ForeignKey(
        "Dataset", on_delete=models.CASCADE, related_name="raw_data_sources"
    )
    # update_frequency = models.ForeignKey(...)
    # license = models.ForeignKey(...)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(unique=True)
    name_en = models.CharField(max_length=255)
    name_pt = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    raw_data_url = models.URLField(blank=True, null=True)
    auxiliary_files_url = models.URLField(blank=True, null=True)
    architecture_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return str(self.slug)

    class Meta:
        db_table = "raw_data_source"
        verbose_name = "Raw Data Source"
        verbose_name_plural = "Raw Data Sources"
        ordering = ["slug"]


class InformationRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    dataset = models.ForeignKey(
        "Dataset", on_delete=models.CASCADE, related_name="information_requests"
    )
    # update_frequency = models.ForeignKey(...)
    # license = models.ForeignKey(...)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(unique=True)
    name_en = models.CharField(max_length=255)
    name_pt = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    raw_data_url = models.URLField(blank=True, null=True)
    auxiliary_files_url = models.URLField(blank=True, null=True)
    architecture_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return str(self.slug)

    class Meta:
        db_table = "information_request"
        verbose_name = "Information Request"
        verbose_name_plural = "Information Requests"
        ordering = ["slug"]
