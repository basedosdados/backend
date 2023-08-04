# -*- coding: utf-8 -*-
from uuid import uuid4

import calendar
from datetime import datetime

import os
from django.core.exceptions import ValidationError
from django import forms
from django.db import models
from django.urls import reverse

from ordered_model.models import OrderedModel

from basedosdados_api.account.models import Account
from basedosdados_api.account.storage import OverwriteStorage
from basedosdados_api.api.v1.utils import (
    check_kebab_case,
    check_snake_case,
)
from basedosdados_api.api.v1.validators import validate_is_valid_image_format
from basedosdados_api.custom.model import BdmModel


def image_path_and_rename(instance, filename):
    """
    Rename file to be the username
    """
    upload_to = instance.__class__.__name__.lower()
    ext = filename.split(".")[-1]
    # get filename
    filename = f"{instance.pk}.{ext}"
    return os.path.join(upload_to, filename)


def get_date_time(date_times):
    """Returns a DateTimeRange object with the minimum start date and maximum end date"""
    start_year, start_month, start_day = False, False, False
    end_year, end_month, end_day = False, False, False
    start_date, end_date = datetime(3000, 12, 31, 0, 0, 0), datetime(1, 1, 1, 0, 0, 0)

    for date_time in date_times:
        if date_time.start_year and date_time.start_year < start_date.year:
            start_year = date_time.start_year
        if date_time.start_month and date_time.start_month < start_date.month:
            start_month = date_time.start_month
        if date_time.start_day and date_time.start_day < start_date.day:
            start_day = date_time.start_day
        if date_time.end_year and date_time.end_year > end_date.year:
            end_year = date_time.end_year
        if date_time.end_month and date_time.end_month > end_date.month:
            end_month = date_time.end_month
        if date_time.end_day and date_time.end_day > end_date.day:
            end_day = date_time.end_day

    return DateTimeRange(
        start_year=start_year,
        start_month=start_month,
        start_day=start_day,
        end_year=end_year,
        end_month=end_month,
        end_day=end_day,
    )


class UUIDHIddenIdForm(forms.ModelForm):
    id = forms.UUIDField(widget=forms.HiddenInput(), required=False)

    class Meta:
        abstract = True


class Area(BdmModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255, blank=False, null=False)

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return f"{str(self.name)} ({str(self.slug)})"

    class Meta:
        db_table = "area"
        verbose_name = "Area"
        verbose_name_plural = "Areas"
        ordering = ["name"]


class Coverage(BdmModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    table = models.ForeignKey(
        "Table",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="coverages",
    )
    raw_data_source = models.ForeignKey(
        "RawDataSource",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="coverages",
    )
    information_request = models.ForeignKey(
        "InformationRequest",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="coverages",
    )
    column = models.ForeignKey(
        "Column",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="coverages",
    )
    key = models.ForeignKey(
        "Key",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="coverages",
    )
    analysis = models.ForeignKey(
        "Analysis",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="coverages",
    )
    area = models.ForeignKey("Area", on_delete=models.CASCADE, related_name="coverages")
    is_closed = models.BooleanField("Is Closed", default=False)

    graphql_nested_filter_fields_whitelist = ["id"]

    class Meta:
        db_table = "coverage"
        verbose_name = "Coverage"
        verbose_name_plural = "Coverages"
        ordering = ["id"]

    def __str__(self):
        if self.coverage_type() == "table":
            return f"Table: {self.table} - {self.area}"
        if self.coverage_type() == "raw_data_source":
            return f"Raw data source: {self.raw_data_source} - {self.area}"
        if self.coverage_type() == "information_request":
            return f"Information request: {self.information_request} - {self.area}"
        if self.coverage_type() == "column":
            return f"Column: {self.column} - {self.area}"
        if self.coverage_type() == "key":
            return f"Key: {self.key} - {self.area}"
        if self.coverage_type() == "analysis":
            return f"Key: {self.key} - {self.area}"

        return str(self.id)

    def coverage_type(self):
        if self.table:
            return "table"

        if self.raw_data_source:
            return "raw_data_source"

        if self.information_request:
            return "information_request"

        if self.column:
            return "column"

        if self.key:
            return "key"

        if self.analysis:
            return "analysis"

    coverage_type.short_description = "Coverage Type"

    def clean(self) -> None:
        # Assert that only one of "table", "raw_data_source", "information_request", "column" or
        # "key" is set
        count = 0
        if self.table:
            count += 1
        if self.raw_data_source:
            count += 1
        if self.information_request:
            count += 1
        if self.column:
            count += 1
        if self.key:
            count += 1
        if self.analysis:
            count += 1
        if count != 1:
            raise ValidationError(
                "One and only one of 'table', 'raw_data_source', 'information_request', 'column', 'key', 'analysis' must be set."  # noqa
            )


class License(BdmModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)
    url = models.URLField()

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return str(self.slug)

    class Meta:
        db_table = "license"
        verbose_name = "License"
        verbose_name_plural = "Licenses"
        ordering = ["slug"]


class Key(BdmModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    dictionary = models.ForeignKey(
        "Dictionary", on_delete=models.CASCADE, related_name="keys"
    )
    name = models.CharField(max_length=255)
    value = models.CharField(max_length=255)

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return str(self.name)

    class Meta:
        db_table = "keys"
        verbose_name = "Key"
        verbose_name_plural = "Keys"
        ordering = ["name"]


class Pipeline(BdmModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    github_url = models.URLField()

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return str(self.github_url)

    class Meta:
        db_table = "pipeline"
        verbose_name = "Pipeline"
        verbose_name_plural = "Pipelines"
        ordering = ["github_url"]


class Analysis(BdmModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    name = models.CharField(null=True, blank=True, max_length=255)
    description = models.TextField(null=True, blank=True)
    analysis_type = models.ForeignKey(
        "AnalysisType", on_delete=models.CASCADE, related_name="analyses"
    )
    datasets = models.ManyToManyField(
        "Dataset",
        related_name="analyses",
        help_text="Datasets used in the analysis",
    )
    themes = models.ManyToManyField(
        "Theme",
        related_name="analyses",
        help_text="Themes are used to group analyses by topic",
    )
    tags = models.ManyToManyField(
        "Tag",
        related_name="analyses",
        blank=True,
        help_text="Tags are used to group analyses by topic",
    )
    authors = models.ManyToManyField(
        Account,
        related_name="analyses",
        blank=True,
        help_text="People who performed and/or wrote the analysis",
    )
    url = models.URLField(blank=True, null=True, max_length=255)

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return str(self.name)

    class Meta:
        db_table = "analysis"
        verbose_name = "Analysis"
        verbose_name_plural = "Analyses"
        ordering = ["name"]


class AnalysisType(BdmModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return str(self.name)

    class Meta:
        db_table = "analysis_type"
        verbose_name = "Analysis Type"
        verbose_name_plural = "Analysis Types"
        ordering = ["name"]


class Tag(BdmModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return str(self.slug)

    class Meta:
        db_table = "tag"
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ["slug"]


class Theme(BdmModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return str(self.slug)

    class Meta:
        db_table = "theme"
        verbose_name = "Theme"
        verbose_name_plural = "Themes"
        ordering = ["slug"]


class Organization(BdmModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=False, max_length=255)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    area = models.ForeignKey(
        "Area", on_delete=models.CASCADE, related_name="organizations"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    website = models.URLField(blank=True, null=True, max_length=255)
    twitter = models.URLField(blank=True, null=True)
    facebook = models.URLField(blank=True, null=True)
    linkedin = models.URLField(blank=True, null=True)
    instagram = models.URLField(blank=True, null=True)
    picture = models.ImageField(
        "Imagem",
        upload_to=image_path_and_rename,
        null=True,
        blank=True,
        validators=[validate_is_valid_image_format],
        storage=OverwriteStorage(),
    )

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return str(self.slug)

    class Meta:
        db_table = "organization"
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"
        ordering = ["slug"]

    def has_picture(self):
        try:
            hasattr(self.picture, "url")
        except Exception as e:  # noqa
            return False
        return self.picture is not None

    has_picture.short_description = "Has Picture"
    has_picture.boolean = True

    @property
    def get_graphql_has_picture(self):
        return self.has_picture()

    @property
    def full_slug(self):
        if self.area.slug != "unknown":
            return f"{self.area.slug}_{self.slug}"
        else:
            return f"{self.slug}"

    @property
    def get_graphql_full_slug(self):
        return self.full_slug


class Status(BdmModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)

    def __str__(self) -> str:
        return str(self.slug)

    graphql_nested_filter_fields_whitelist = ["id"]

    class Meta:
        db_table = "status"
        verbose_name = "Status"
        verbose_name_plural = "Statuses"
        ordering = ["slug"]


class Dataset(BdmModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=False, max_length=255)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    organization = models.ForeignKey(
        "Organization", on_delete=models.CASCADE, related_name="datasets"
    )
    themes = models.ManyToManyField(
        "Theme",
        related_name="datasets",
        help_text="Themes are used to group datasets by topic",
    )
    tags = models.ManyToManyField(
        "Tag",
        related_name="datasets",
        blank=True,
        help_text="Tags are used to group datasets by topic",
    )
    version = models.IntegerField(null=True, blank=True)
    status = models.ForeignKey(
        "Status",
        on_delete=models.PROTECT,
        related_name="datasets",
        null=True,
        blank=True,
        help_text="Status is used to indicate at what stage of development or publishing the dataset is.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_closed = models.BooleanField(
        default=False, help_text="Dataset is for BD Pro subscribers only"
    )

    graphql_nested_filter_fields_whitelist = ["id", "slug"]

    def __str__(self):
        return str(self.slug)

    class Meta:
        db_table = "dataset"
        verbose_name = "Dataset"
        verbose_name_plural = "Datasets"
        ordering = ["slug"]

    def get_success_url(self):
        return reverse("datasetdetail", kwargs={"pk": self.object.pk})

    @property
    def full_slug(self):
        if self.organization.area.slug != "unknown":
            return f"{self.organization.area.slug}_{self.organization.slug}_{self.slug}"
        else:
            return f"{self.organization.slug}_{self.slug}"

    @property
    def get_graphql_full_slug(self):
        return self.full_slug

    @property
    def coverage(self):
        tables = self.tables.all()
        raw_data_sources = self.raw_data_sources.all()
        information_requests = self.information_requests.all()
        start_year, start_month, start_day = False, False, False
        end_year, end_month, end_day = False, False, False

        start_date = datetime(3000, 12, 31, 0, 0, 0)
        end_date = datetime(1, 1, 1, 0, 0, 0)

        # TODO: refactor this to use a function
        for table in tables:
            for coverage in table.coverages.all():
                date_times = DateTimeRange.objects.filter(coverage=coverage.pk)
                if len(date_times) == 0:
                    continue
                date_time = get_date_time(date_times)

                start_year = (
                    date_time.start_year if date_time.start_year else start_year
                )
                start_month = (
                    date_time.start_month if date_time.start_month else start_month
                )
                start_day = date_time.start_day if date_time.start_day else start_day
                end_year = date_time.end_year if date_time.end_year else end_year
                end_month = date_time.end_month if date_time.end_month else end_month
                end_day = date_time.end_day if date_time.end_day else end_day

                new_start_date = datetime(
                    date_time.start_year or 3000,
                    date_time.start_month or 1,
                    date_time.start_day or 1,
                )
                start_date = (
                    new_start_date if new_start_date < start_date else start_date
                )
                new_end_date = datetime(
                    date_time.end_year or 1,
                    date_time.end_month or 1,
                    date_time.end_day or 1,
                )
                end_date = new_end_date if new_end_date > end_date else end_date

        for raw_data_source in raw_data_sources:
            for coverage in raw_data_source.coverages.all():
                date_times = DateTimeRange.objects.filter(coverage=coverage.pk)
                if len(date_times) == 0:
                    continue
                date_time = get_date_time(date_times)

                start_year = (
                    date_time.start_year if date_time.start_year else start_year
                )
                start_month = (
                    date_time.start_month if date_time.start_month else start_month
                )
                start_day = date_time.start_day if date_time.start_day else start_day
                end_year = date_time.end_year if date_time.end_year else end_year
                end_month = date_time.end_month if date_time.end_month else end_month
                end_day = date_time.end_day if date_time.end_day else end_day

                new_start_date = datetime(
                    date_time.start_year or 3000,
                    date_time.start_month or 1,
                    date_time.start_day or 1,
                )
                start_date = (
                    new_start_date if new_start_date < start_date else start_date
                )
                new_end_date = datetime(
                    date_time.end_year or 1,
                    date_time.end_month or 1,
                    date_time.end_day or 1,
                )
                end_date = new_end_date if new_end_date > end_date else end_date

        for information_request in information_requests:
            for coverage in information_request.coverages.all():
                date_times = DateTimeRange.objects.filter(coverage=coverage.pk)
                if len(date_times) == 0:
                    continue
                date_time = get_date_time(date_times)

                start_year = (
                    date_time.start_year if date_time.start_year else start_year
                )
                start_month = (
                    date_time.start_month if date_time.start_month else start_month
                )
                start_day = date_time.start_day if date_time.start_day else start_day
                end_year = date_time.end_year if date_time.end_year else end_year
                end_month = date_time.end_month if date_time.end_month else end_month
                end_day = date_time.end_day if date_time.end_day else end_day

                new_start_date = datetime(
                    date_time.start_year or 3000,
                    date_time.start_month or 1,
                    date_time.start_day or 1,
                )
                start_date = (
                    new_start_date if new_start_date < start_date else start_date
                )
                new_end_date = datetime(
                    date_time.end_year or 1,
                    date_time.end_month or 1,
                    date_time.end_day or 1,
                )
                end_date = new_end_date if new_end_date > end_date else end_date

        start = []
        end = []

        if start_year < 3000 and start_date.year:
            start.append(str(start_date.year))
            if start_month and start_date.month:
                start.append(str(start_date.month).zfill(2))
                if start_day and start_date.day:
                    start.append(str(start_date.day).zfill(2))

        if end_year > 1 and end_date.year:
            end.append(str(end_date.year))
            if end_month and end_date.month:
                end.append(str(end_date.month).zfill(2))
                if end_day and end_date.day:
                    end.append(str(end_date.day).zfill(2))

        return "-".join(start) + " - " + "-".join(end)

    @property
    def get_graphql_coverage(self):
        return self.coverage

    @property
    def contains_tables(self):
        return len(self.tables.all()) > 0

    @property
    def get_graphql_contains_tables(self):
        return self.contains_tables

    @property
    def contains_closed_data(self):
        """Returns true if there are tables or columns with closed coverages"""
        closed_data = False
        tables = self.tables.all()
        for table in tables:
            table_coverages = table.coverages.filter(is_closed=True)
            if table_coverages:
                closed_data = True
                break
            for column in table.columns.all():
                if column.is_closed:  # in the future it will be column.coverages
                    closed_data = True
                    break

        return closed_data

    @property
    def get_graphql_contains_closed_data(self):
        return self.contains_closed_data

    @property
    def contains_open_data(self):
        """Returns true if there are tables or columns with open coverages"""
        open_data = False
        tables = self.tables.all()
        for table in tables:
            table_coverages = table.coverages.filter(is_closed=False)
            if table_coverages:
                open_data = True
                break

        return open_data

    @property
    def get_graphql_contains_open_data(self):
        return self.contains_open_data

    @property
    def contains_closed_tables(self):
        closed_tables = self.tables.all().filter(is_closed=True)
        return len(closed_tables) > 0

    @property
    def get_graphql_contains_closed_tables(self):
        return self.contains_closed_tables

    @property
    def contains_open_tables(self):
        open_tables = self.tables.all().filter(is_closed=False)
        return len(open_tables) > 0

    @property
    def get_graphql_contains_open_tables(self):
        return self.contains_open_tables

    @property
    def contains_raw_data_sources(self):
        return len(self.raw_data_sources.all()) > 0

    @property
    def get_graphql_contains_raw_data_sources(self):
        return self.contains_raw_data_sources

    @property
    def contains_information_requests(self):
        return len(self.information_requests.all()) > 0

    @property
    def get_graphql_contains_information_requests(self):
        return self.contains_information_requests


class Update(BdmModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    entity = models.ForeignKey(
        "Entity", on_delete=models.CASCADE, related_name="updates"
    )
    frequency = models.IntegerField()
    lag = models.IntegerField(blank=True, null=True)
    latest = models.DateTimeField(blank=True, null=True)
    table = models.ForeignKey(
        "Table",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="updates",
    )
    raw_data_source = models.ForeignKey(
        "RawDataSource",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="updates",
    )
    information_request = models.ForeignKey(
        "InformationRequest",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="updates",
    )

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return f"{str(self.frequency)} {str(self.entity)}"

    class Meta:
        db_table = "update"
        verbose_name = "Update"
        verbose_name_plural = "Updates"
        ordering = ["frequency"]

    def clean(self) -> None:

        # Assert that only one of "table", "raw_data_source", "information_request" is set
        count = 0
        if self.table:
            count += 1
        if self.raw_data_source:
            count += 1
        if self.information_request:
            count += 1
        if count != 1:
            raise ValidationError(
                "One and only one of 'table', 'raw_data_source', or 'information_request' must be set."  # noqa
            )

        if self.entity.category.slug != "datetime":
            raise ValidationError(
                "Entity's category is not in category.slug = `datetime`."
            )

        return super().clean()


class Table(BdmModel, OrderedModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=False, max_length=255)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    dataset = models.ForeignKey(
        "Dataset", on_delete=models.CASCADE, related_name="tables"
    )
    version = models.IntegerField(null=True, blank=True)
    status = models.ForeignKey(
        "Status", on_delete=models.PROTECT, related_name="tables", null=True, blank=True
    )
    license = models.ForeignKey(
        "License",
        on_delete=models.CASCADE,
        related_name="tables",
        blank=True,
        null=True,
    )
    partner_organization = models.ForeignKey(
        "Organization",
        on_delete=models.CASCADE,
        related_name="partner_tables",
        blank=True,
        null=True,
    )
    pipeline = models.ForeignKey(
        "Pipeline",
        on_delete=models.CASCADE,
        related_name="tables",
        blank=True,
        null=True,
    )
    is_directory = models.BooleanField(default=False, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_by = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="tables_published",
        blank=True,
        null=True,
    )
    data_cleaned_by = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="tables_cleaned",
        blank=True,
        null=True,
    )
    data_cleaning_description = models.TextField(blank=True, null=True)
    data_cleaning_code_url = models.URLField(blank=True, null=True)
    raw_data_url = models.URLField(blank=True, null=True, max_length=500)
    auxiliary_files_url = models.URLField(blank=True, null=True)
    architecture_url = models.URLField(blank=True, null=True)
    source_bucket_name = models.CharField(max_length=255, blank=True, null=True)
    uncompressed_file_size = models.BigIntegerField(blank=True, null=True)
    compressed_file_size = models.BigIntegerField(blank=True, null=True)
    number_rows = models.BigIntegerField(blank=True, null=True)
    number_columns = models.BigIntegerField(blank=True, null=True)
    is_closed = models.BooleanField(
        default=False, help_text="Table is for BD Pro subscribers only"
    )
    order_with_respect_to = ("dataset",)

    graphql_nested_filter_fields_whitelist = ["id", "dataset"]

    def __str__(self):
        return f"{str(self.dataset.slug)}.{str(self.slug)}"

    class Meta:
        db_table = "table"
        verbose_name = "Table"
        verbose_name_plural = "Tables"
        ordering = ["slug"]
        constraints = [
            models.UniqueConstraint(
                fields=["dataset", "slug"], name="constraint_dataset_table_slug"
            )
        ]

    @property
    def partitions(self):
        partitions_list = [p.name for p in self.columns.all().filter(is_partition=True)]
        return ", ".join(partitions_list)

    @property
    def get_graphql_partitions(self):
        return self.partitions

    @property
    def contains_closed_data(self):
        """Returns true if there are columns with closed coverages"""
        closed_data = False
        table_coverages = self.coverages.filter(is_closed=True)
        if table_coverages:
            closed_data = True
        for column in self.columns.all():  # in the future it will be column.coverages
            if column.is_closed:
                closed_data = True
                break

        return closed_data

    @property
    def get_graphql_contains_closed_data(self):
        return self.contains_closed_data

    def clean(self):
        errors = {}
        """Coverages must not overlap"""
        coverages = self.coverages.all()
        for coverage in coverages:
            temporal_coverages = [d for d in coverage.datetime_ranges.all()]
            dt_ranges = []
            for idx, temporal_coverage in enumerate(temporal_coverages):
                dt_ranges.append(
                    (
                        datetime(
                            temporal_coverage.start_year,
                            temporal_coverage.start_month or 1,
                            temporal_coverage.start_day or 1,
                        ),
                        datetime(
                            temporal_coverage.end_year or datetime.now().year,
                            temporal_coverage.end_month or 1,
                            temporal_coverage.end_day or 1,
                        ),
                    )
                )
            dt_ranges.sort(key=lambda x: x[0])
            for i in range(1, len(dt_ranges)):
                if dt_ranges[i - 1][1] > dt_ranges[i][0]:
                    errors = "Temporal coverages must not overlap"

        if errors:
            raise ValidationError(errors)


class BigQueryType(BdmModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    name = models.CharField(max_length=255)

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return str(self.name)

    class Meta:
        db_table = "bigquery_type"
        verbose_name = "BigQuery Type"
        verbose_name_plural = "BigQuery Types"
        ordering = ["name"]


class Column(BdmModel, OrderedModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    table = models.ForeignKey("Table", on_delete=models.CASCADE, related_name="columns")
    name = models.CharField(max_length=255)
    name_staging = models.CharField(max_length=255, blank=True, null=True)
    bigquery_type = models.ForeignKey(
        "BigQueryType", on_delete=models.CASCADE, related_name="columns"
    )
    description = models.TextField(blank=True, null=True)
    covered_by_dictionary = models.BooleanField(default=False, blank=True, null=True)
    is_primary_key = models.BooleanField(default=False, blank=True, null=True)
    directory_primary_key = models.ForeignKey(
        "Column",
        on_delete=models.PROTECT,
        related_name="columns",
        blank=True,
        null=True,
    )
    measurement_unit = models.CharField(max_length=255, blank=True, null=True)
    contains_sensitive_data = models.BooleanField(default=False, blank=True, null=True)
    observations = models.TextField(blank=True, null=True)
    is_in_staging = models.BooleanField(default=True)
    is_partition = models.BooleanField(default=False)
    observation_level = models.ForeignKey(
        "ObservationLevel",
        on_delete=models.CASCADE,
        related_name="columns",
        null=True,
        blank=True,
    )
    version = models.IntegerField(null=True, blank=True)
    status = models.ForeignKey(
        "Status",
        on_delete=models.PROTECT,
        related_name="columns",
        null=True,
        blank=True,
    )
    is_closed = models.BooleanField(
        default=False, help_text="Column is for BD Pro subscribers only"
    )
    order_with_respect_to = ("table",)

    graphql_nested_filter_fields_whitelist = ["id", "name"]

    def __str__(self):
        return f"{str(self.table.dataset.slug)}.{self.table.slug}.{str(self.name)}"

    class Meta:
        db_table = "column"
        verbose_name = "Column"
        verbose_name_plural = "Columns"
        ordering = ["name"]

    def clean(self) -> None:

        errors = {}
        if self.observation_level and self.observation_level.table != self.table:
            errors[
                "observation_level"
            ] = "Observation level is not in the same table as the column."

        if (
            self.directory_primary_key
            and self.directory_primary_key.table.is_directory is False
        ):
            errors[
                "directory_primary_key"
            ] = "Column indicated as a directory's primary key is not in a directory."

        if errors:
            raise ValidationError(errors)

        return super().clean()


class Dictionary(BdmModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    column = models.ForeignKey(
        "Column", on_delete=models.CASCADE, related_name="dictionaries"
    )

    graphql_nested_filter_fields_whitelist = ["id"]

    class Meta:
        verbose_name = "Dictionary"
        verbose_name_plural = "Dictionaries"
        ordering = ["column"]

    def __str__(self):
        return f"{str(self.column.table.dataset.slug)}.{self.column.table.slug}.{str(self.column.name)}"


class CloudTable(BdmModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    table = models.ForeignKey(
        "Table", on_delete=models.CASCADE, related_name="cloud_tables"
    )
    columns = models.ManyToManyField(
        "Column",
        related_name="cloud_tables",
        blank=True,
    )
    gcp_project_id = models.CharField(max_length=255)
    gcp_dataset_id = models.CharField(max_length=255)
    gcp_table_id = models.CharField(max_length=255)

    graphql_nested_filter_fields_whitelist = [
        "id",
        "gcp_project_id",
        "gcp_dataset_id",
        "gcp_table_id",
    ]

    def __str__(self):
        return f"{self.gcp_project_id}.{self.gcp_dataset_id}.{self.gcp_table_id}"

    def clean(self) -> None:
        errors = {}
        if self.gcp_project_id and not check_kebab_case(self.gcp_project_id):
            errors["gcp_project_id"] = "gcp_project_id must be in kebab-case."
        if self.gcp_project_id and not check_snake_case(self.gcp_dataset_id):
            errors["gcp_dataset_id"] = "gcp_dataset_id must be in snake_case."
        if self.gcp_table_id and not check_snake_case(self.gcp_table_id):
            errors["gcp_table_id"] = "gcp_table_id must be in snake_case."
        for column in self.columns.all():
            if column.table != self.table:
                errors[
                    "columns"
                ] = f"Column {column} does not belong to table {self.table}."
        if errors:
            raise ValidationError(errors)

        return super().clean()

    class Meta:
        db_table = "cloud_table"
        verbose_name = "Cloud Table"
        verbose_name_plural = "Cloud Tables"
        ordering = ["id"]


class Availability(BdmModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return str(self.slug)

    class Meta:
        db_table = "availability"
        verbose_name = "Availability"
        verbose_name_plural = "Availabilities"
        ordering = ["slug"]


class Language(BdmModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return str(self.slug)

    class Meta:
        db_table = "language"
        verbose_name = "Language"
        verbose_name_plural = "Languages"
        ordering = ["slug"]


class RawDataSource(BdmModel, OrderedModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    url = models.URLField(max_length=500, blank=True, null=True)
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
    area_ip_address_required = models.ManyToManyField(
        "Area", related_name="raw_data_sources", blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    contains_structured_data = models.BooleanField(default=False)
    contains_api = models.BooleanField(default=False)
    is_free = models.BooleanField(default=False)
    required_registration = models.BooleanField(default=False)
    version = models.IntegerField(null=True, blank=True)
    status = models.ForeignKey(
        "Status",
        on_delete=models.PROTECT,
        related_name="raw_data_sources",
        null=True,
        blank=True,
    )
    order_with_respect_to = ("dataset",)

    graphql_nested_filter_fields_whitelist = ["id"]

    class Meta:
        db_table = "raw_data_source"
        verbose_name = "Raw Data Source"
        verbose_name_plural = "Raw Data Sources"
        ordering = ["url"]

    def __str__(self):
        return f"{self.name} ({self.dataset.name})"


class InformationRequest(BdmModel, OrderedModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    dataset = models.ForeignKey(
        "Dataset", on_delete=models.CASCADE, related_name="information_requests"
    )
    version = models.IntegerField(null=True, blank=True)
    status = models.ForeignKey(
        "Status",
        on_delete=models.CASCADE,
        related_name="information_requests",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    origin = models.TextField(max_length=500, blank=True, null=True)
    number = models.CharField(max_length=255)
    url = models.URLField(blank=True, max_length=500, null=True)
    started_at = models.DateTimeField(blank=True, null=True)
    data_url = models.URLField(max_length=500, blank=True, null=True)
    observations = models.TextField(blank=True, null=True)
    started_by = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="information_requests",
        blank=True,
        null=True,
    )
    order_with_respect_to = ("dataset",)

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return str(f"{self.dataset.name}({self.number})")

    class Meta:
        db_table = "information_request"
        verbose_name = "Information Request"
        verbose_name_plural = "Information Requests"
        ordering = ["number"]

    def clean(self) -> None:
        errors = {}
        if self.origin is not None and len(self.origin) > 500:
            errors["origin"] = "Origin cannot be longer than 500 characters"
        if errors:
            raise ValidationError(errors)

        return super().clean()


class EntityCategory(BdmModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return str(self.slug)

    class Meta:
        db_table = "entity_category"
        verbose_name = "Entity Category"
        verbose_name_plural = "Entity Categories"
        ordering = ["slug"]


class Entity(BdmModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)
    category = models.ForeignKey(
        "EntityCategory", on_delete=models.CASCADE, related_name="entities"
    )

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return str(self.slug)

    class Meta:
        db_table = "entity"
        verbose_name = "Entity"
        verbose_name_plural = "Entities"
        ordering = ["slug"]


class ObservationLevel(BdmModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    entity = models.ForeignKey(
        "Entity", on_delete=models.CASCADE, related_name="observation_levels"
    )
    table = models.ForeignKey(
        "Table",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="observation_levels",
    )
    raw_data_source = models.ForeignKey(
        "RawDataSource",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="observation_levels",
    )
    information_request = models.ForeignKey(
        "InformationRequest",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="observation_levels",
    )
    analysis = models.ForeignKey(
        "Analysis",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="observation_levels",
    )

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return str(self.entity)

    class Meta:
        db_table = "observation_level"
        verbose_name = "Observation Level"
        verbose_name_plural = "Observation Levels"
        ordering = ["id"]

    def clean(self) -> None:
        # Assert that only one of "table", "raw_data_source", "information_request" is set
        count = 0
        if self.table:
            count += 1
        if self.raw_data_source:
            count += 1
        if self.information_request:
            count += 1
        if self.analysis:
            count += 1
        if count != 1:
            raise ValidationError(
                "One and only one of 'table', 'raw_data_source', 'information_request', 'analysis' must be set."  # noqa
            )
        return super().clean()


class DateTimeRange(BdmModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    coverage = models.ForeignKey(
        "Coverage", on_delete=models.CASCADE, related_name="datetime_ranges"
    )
    start_year = models.IntegerField(blank=True, null=True)
    start_semester = models.IntegerField(blank=True, null=True)
    start_quarter = models.IntegerField(blank=True, null=True)
    start_month = models.IntegerField(blank=True, null=True)
    start_day = models.IntegerField(blank=True, null=True)
    start_hour = models.IntegerField(blank=True, null=True)
    start_minute = models.IntegerField(blank=True, null=True)
    start_second = models.IntegerField(blank=True, null=True)
    end_year = models.IntegerField(blank=True, null=True)
    end_semester = models.IntegerField(blank=True, null=True)
    end_quarter = models.IntegerField(blank=True, null=True)
    end_month = models.IntegerField(blank=True, null=True)
    end_day = models.IntegerField(blank=True, null=True)
    end_hour = models.IntegerField(blank=True, null=True)
    end_minute = models.IntegerField(blank=True, null=True)
    end_second = models.IntegerField(blank=True, null=True)
    interval = models.IntegerField(blank=True, null=True)

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        start_year = self.start_year or ""
        start_month = f"-{self.start_month}" if self.start_month else ""
        start_day = f"-{self.start_day}" if self.start_day else ""
        start_hour = f" {self.start_hour}" if self.start_hour else ""
        start_minute = f":{self.start_minute}" if self.start_minute else ""
        start_second = f":{self.start_second}" if self.start_second else ""
        end_year = self.end_year or ""
        end_month = f"-{self.end_month}" if self.end_month else ""
        end_day = f"-{self.end_day}" if self.end_day else ""
        end_hour = f" {self.end_hour}" if self.end_hour else ""
        end_minute = f":{self.end_minute}" if self.end_minute else ""
        end_second = f":{self.end_second}" if self.end_second else ""
        interval = f"({self.interval})" if self.interval else "()"
        return f"{start_year}{start_month}{start_day}{start_hour}{start_minute}{start_second}{interval}\
           {end_year}{end_month}{end_day}{end_hour}{end_minute}{end_second}"

    class Meta:
        db_table = "datetime_range"
        verbose_name = "DateTime Range"
        verbose_name_plural = "DateTime Ranges"
        ordering = ["id"]

    def clean(self) -> None:
        errors = {}

        if (self.start_year and self.end_year) and self.start_year > self.end_year:
            errors["start_year"] = ["Start year cannot be greater than end year"]

        if self.start_year and self.end_year:
            try:
                start_datetime = datetime(
                    self.start_year,
                    self.start_month or 1,
                    self.start_day or 1,
                    self.start_hour or 0,
                    self.start_minute or 0,
                    self.start_second or 0,
                )
                end_datetime = datetime(
                    self.end_year,
                    self.end_month or 1,
                    self.end_day or 1,
                    self.end_hour or 0,
                    self.end_minute or 0,
                    self.end_second or 0,
                )
                if start_datetime > end_datetime:
                    errors["start_year"] = [
                        "Start datetime cannot be greater than end datetime"
                    ]

            except TypeError:
                errors["start_year"] = ["Start year or end year are invalid"]

        if self.start_day:
            max_day = calendar.monthrange(self.start_year, self.start_month)[1]
            if self.start_day > max_day:
                errors["start_day"] = [
                    f"{self.start_month} does not have {self.start_day} days in {self.start_year}"
                ]

        if self.end_day:
            max_day = calendar.monthrange(self.end_year, self.end_month)[1]
            if self.end_day > max_day:
                errors["end_day"] = [
                    f"{self.end_month} does not have {self.end_day} days in {self.end_year}"
                ]

        if self.start_semester:
            if self.start_semester > 2:
                errors["start_semester"] = ["Semester cannot be greater than 2"]

        if self.end_semester:
            if self.end_semester > 2:
                errors["end_semester"] = ["Semester cannot be greater than 2"]

        if self.start_quarter:
            if self.start_quarter > 4:
                errors["start_quarter"] = ["Quarter cannot be greater than 4"]

        if self.end_quarter:
            if self.end_quarter > 4:
                errors["end_quarter"] = ["Quarter cannot be greater than 4"]

        if self.start_month:
            if self.start_month > 12:
                errors["start_month"] = ["Month cannot be greater than 12"]

        if self.end_month:
            if self.end_month > 12:
                errors["end_month"] = ["Month cannot be greater than 12"]

        if errors:
            raise ValidationError(errors)

        return super().clean()


class QualityCheck(BdmModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    name = models.CharField(null=True, blank=True, max_length=255)
    description = models.TextField(null=True, blank=True)
    passed = models.BooleanField(default=False, help_text="Passed the quality check")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    pipeline = models.ForeignKey(
        "Pipeline",
        on_delete=models.CASCADE,
        related_name="quality_checks",
        blank=True,
        null=True,
    )
    analysis = models.ForeignKey(
        "Analysis",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="quality_checks",
    )
    dataset = models.ForeignKey(
        "Dataset",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="quality_checks",
    )
    table = models.ForeignKey(
        "Table",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="quality_checks",
    )
    column = models.ForeignKey(
        "Column",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="quality_checks",
    )
    key = models.ForeignKey(
        "Key",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="quality_checks",
    )
    raw_data_source = models.ForeignKey(
        "RawDataSource",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="quality_checks",
    )
    information_request = models.ForeignKey(
        "InformationRequest",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="quality_checks",
    )

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return str(self.name)

    class Meta:
        db_table = "quality_check"
        verbose_name = "Quality Check"
        verbose_name_plural = "Quality Checks"
        ordering = ["id"]

    def clean(self) -> None:
        count = 0
        if self.analysis:
            count += 1
        if self.dataset:
            count += 1
        if self.table:
            count += 1
        if self.column:
            count += 1
        if self.key:
            count += 1
        if self.raw_data_source:
            count += 1
        if self.information_request:
            count += 1
        if count != 1:
            raise ValidationError(
                "One and only one of 'analysis', 'dataset, 'table', 'column', 'key, 'raw_data_source', 'information_request' must be set."  # noqa
            )
        return super().clean()
