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
    area_ip_address_required = models.BooleanField(default=False)

    def __str__(self):
        return str(self.slug)

    class Meta:
        db_table = "area"
        verbose_name = "Area"
        verbose_name_plural = "Areas"
        ordering = ["slug"]


class Coverage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    area = models.ForeignKey("Area", on_delete=models.CASCADE, related_name="coverages")
    temporal_coverage = models.CharField(max_length=255)

    def __str__(self):
        return str(self.temporal_coverage)

    class Meta:
        db_table = "coverage"
        verbose_name = "Coverage"
        verbose_name_plural = "Coverages"
        ordering = ["temporal_coverage"]


class License(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name_en = models.CharField(max_length=255)
    name_pt = models.CharField(max_length=255)
    url = models.URLField()

    def __str__(self):
        return str(self.slug)

    class Meta:
        db_table = "license"
        verbose_name = "License"
        verbose_name_plural = "Licenses"
        ordering = ["slug"]


class Key(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    coverages = models.ManyToManyField("Coverage", related_name="keys")
    name = models.CharField(max_length=255)
    value = models.CharField(max_length=255)


class AnalysisType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    name_en = models.CharField(max_length=255)
    name_pt = models.CharField(max_length=255)
    tag_en = models.CharField(max_length=255)
    tag_pt = models.CharField(max_length=255)

    def __str__(self):
        return str(self.name_pt)

    class Meta:
        db_table = "analysis_type"
        verbose_name = "Analysis Type"
        verbose_name_plural = "Analysis Types"
        ordering = ["name_pt"]


class Tag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name_en = models.CharField(max_length=255)
    name_pt = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.slug)

    class Meta:
        db_table = "tag"
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ["slug"]


class Theme(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name_en = models.CharField(max_length=255)
    name_pt = models.CharField(max_length=255)
    logo_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.slug)

    class Meta:
        db_table = "theme"
        verbose_name = "Theme"
        verbose_name_plural = "Themes"
        ordering = ["slug"]


class Entity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name_en = models.CharField(max_length=255)
    name_pt = models.CharField(max_length=255)

    def __str__(self):
        return str(self.slug)

    class Meta:
        db_table = "entity"
        verbose_name = "Entity"
        verbose_name_plural = "Entities"
        ordering = ["slug"]


class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    # Foreign
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


class TimeUnit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name_en = models.CharField(max_length=255)
    name_pt = models.CharField(max_length=255)

    def __str__(self):
        return str(self.slug)

    class Meta:
        db_table = "time_unit"
        verbose_name = "Time Unit"
        verbose_name_plural = "Time Units"
        ordering = ["slug"]


class UpdateFrequency(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    time_unit = models.ForeignKey(
        "TimeUnit", on_delete=models.CASCADE, related_name="update_frequencies"
    )
    number = models.IntegerField()

    def __str__(self):
        return str(self.number + " " + self.time_unit)

    class Meta:
        db_table = "update_frequency"
        verbose_name = "Update Frequency"
        verbose_name_plural = "Update Frequencies"
        ordering = ["number"]


class Table(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    dataset = models.ForeignKey(
        "Dataset", on_delete=models.CASCADE, related_name="tables"
    )
    license = models.ForeignKey(
        "License", on_delete=models.CASCADE, related_name="tables"
    )
    update_frequency = models.ForeignKey(
        "UpdateFrequency", on_delete=models.CASCADE, related_name="tables"
    )
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


class DirectoryPrimaryKey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return str(self.slug)

    class Meta:
        db_table = "directory_primary_key"
        verbose_name = "Directory Primary Key"
        verbose_name_plural = "Directory Primary Keys"
        ordering = ["slug"]


class Column(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    table = models.ForeignKey("Table", on_delete=models.CASCADE, related_name="columns")
    bigquery_type = models.ForeignKey(
        "BigQueryTypes", on_delete=models.CASCADE, related_name="columns"
    )
    directory_primary_key = models.ForeignKey(
        "DirectoryPrimaryKey",
        on_delete=models.CASCADE,
        related_name="columns",
        blank=True,
        null=True,
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


class Dictionary(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    column = models.OneToOneField(
        "Column", on_delete=models.CASCADE, related_name="dictionary"
    )
    keys = models.ForeignKey(
        "Key", on_delete=models.CASCADE, related_name="dictionaries"
    )


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


class Availability(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name_en = models.CharField(max_length=255)
    name_pt = models.CharField(max_length=255)


class Language(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name_en = models.CharField(max_length=255)
    name_pt = models.CharField(max_length=255)


class RawDataSource(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    dataset = models.ForeignKey(
        "Dataset", on_delete=models.CASCADE, related_name="raw_data_sources"
    )
    availability = models.ForeignKey(
        "Availability", on_delete=models.CASCADE, related_name="raw_data_sources"
    )
    languages = models.ManyToManyField(
        "Language", related_name="raw_data_sources", blank=True
    )
    license = models.ForeignKey(
        "License", on_delete=models.CASCADE, related_name="raw_data_sources"
    )
    update_frequency = models.ForeignKey(
        "UpdateFrequency", on_delete=models.CASCADE, related_name="raw_data_sources"
    )
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


class Status(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name_en = models.CharField(max_length=255)
    name_pt = models.CharField(max_length=255)

    def __str__(self) -> str:
        return str(self.slug)

    class Meta:
        db_table = "status"
        verbose_name = "Status"
        verbose_name_plural = "Statuses"
        ordering = ["slug"]


class InformationRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    dataset = models.ForeignKey(
        "Dataset", on_delete=models.CASCADE, related_name="information_requests"
    )
    status = models.ForeignKey(
        "Status", on_delete=models.CASCADE, related_name="information_requests"
    )
    update_frequency = models.ForeignKey(
        "UpdateFrequency", on_delete=models.CASCADE, related_name="information_requests"
    )
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


class ObservationLevel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    entity = models.ForeignKey(
        "Entity", on_delete=models.CASCADE, related_name="observation_levels"
    )
    tables = models.ManyToManyField("Table", related_name="entity_columns")
    raw_data_sources = models.ManyToManyField(
        "RawDataSource", related_name="entity_columns"
    )
    information_requests = models.ManyToManyField(
        "InformationRequest", related_name="entity_columns"
    )


class EntityColumn(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    entity = models.ForeignKey(
        "Entity", on_delete=models.CASCADE, related_name="entity_columns"
    )
    column = models.ForeignKey(
        "Column", on_delete=models.CASCADE, related_name="entity_columns"
    )
    observation_level = models.ForeignKey(
        "ObservationLevel", on_delete=models.CASCADE, related_name="entity_columns"
    )
