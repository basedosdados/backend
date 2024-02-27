# -*- coding: utf-8 -*-
import calendar
import json
from collections import defaultdict
from datetime import datetime
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from ordered_model.models import OrderedModel

from bd_api.apps.account.models import Account
from bd_api.custom.model import BaseModel
from bd_api.custom.storage import OverwriteStorage, upload_to, validate_image
from bd_api.custom.utils import check_kebab_case, check_snake_case


def to_str(value: str | None, zfill: int = 0):
    """Parse and pad to string if not null"""
    if value is None:
        return None
    return str(value).zfill(zfill)


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


class Area(BaseModel):
    """Area model"""

    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255, blank=False, null=False)

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return f"{str(self.name)} ({str(self.slug)})"

    class Meta:
        """Meta definition for Area."""

        db_table = "area"
        verbose_name = "Area"
        verbose_name_plural = "Areas"
        ordering = ["name"]


class Coverage(BaseModel):
    """
    Coverage model
    Spatial and temporal coverage of a table, raw data source, information request, column or key
    """

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
    column_original_name = models.ForeignKey(
        "ColumnOriginalName",
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
    area = models.ForeignKey(
        "Area",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="coverages",
    )
    is_closed = models.BooleanField("Is Closed", default=False)

    graphql_nested_filter_fields_whitelist = ["id"]

    class Meta:
        """Meta definition for Coverage."""

        db_table = "coverage"
        verbose_name = "Coverage"
        verbose_name_plural = "Coverages"
        ordering = ["id"]

    def __str__(self):
        if self.coverage_type() == "table":
            return f"Table: {self.table} - {self.area}"
        if self.coverage_type() == "column":
            return f"Column: {self.column} - {self.area}"
        if self.coverage_type() == "column_original_name":
            return f"Column: {self.column} - {self.area}"
        if self.coverage_type() == "raw_data_source":
            return f"Raw data source: {self.raw_data_source} - {self.area}"
        if self.coverage_type() == "information_request":
            return f"Information request: {self.information_request} - {self.area}"
        if self.coverage_type() == "key":
            return f"Key: {self.key} - {self.area}"
        if self.coverage_type() == "analysis":
            return f"Analysis: {self.analysis} - {self.area}"
        return str(self.id)

    def coverage_type(self):
        """
        Return the type of coverage. Must be table, raw_data_source,
        information_request, column or key
        """
        if self.table:
            return "table"
        if self.column:
            return "column"
        if self.column_original_name:
            return "column_original_name"
        if self.raw_data_source:
            return "raw_data_source"
        if self.information_request:
            return "information_request"
        if self.key:
            return "key"
        if self.analysis:
            return "analysis"
        return ""

    coverage_type.short_description = "Coverage Type"

    def get_similarity_of_area(self, other: "Coverage"):
        if not self.area:
            return 0
        if not other.area:
            return 0
        if self.area.name.startswith(other.area.name):
            return 1
        if other.area.name.startswith(self.area.name):
            return 1
        return 0

    def get_similarity_of_datetime(self, other: "Coverage"):
        for dt_self in self.datetime_ranges.all():
            for dt_other in other.datetime_ranges.all():
                if dt_self.get_similarity_of_datetime(dt_other):
                    return 1
        return 0

    def clean(self) -> None:
        """
        Assert that only one of "table", "raw_data_source",
        "information_request", "column" or "key" is set
        """
        count = 0
        if self.table:
            count += 1
        if self.column:
            count += 1
        if self.column_original_name:
            count += 1
        if self.raw_data_source:
            count += 1
        if self.information_request:
            count += 1
        if self.key:
            count += 1
        if self.analysis:
            count += 1
        if count != 1:
            raise ValidationError(
                "One and only one of 'table', 'raw_data_source', "
                "'information_request', 'column', 'key', 'analysis' must be set."
            )


class License(BaseModel):
    """License model"""

    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)
    url = models.URLField()

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return str(self.slug)

    class Meta:
        """Meta definition for License."""

        db_table = "license"
        verbose_name = "License"
        verbose_name_plural = "Licenses"
        ordering = ["slug"]


class Key(BaseModel):
    """
    Key model
    Sets a name and a value of a dictionary key
    """

    id = models.UUIDField(primary_key=True, default=uuid4)
    dictionary = models.ForeignKey("Dictionary", on_delete=models.CASCADE, related_name="keys")
    name = models.CharField(max_length=255)
    value = models.CharField(max_length=255)

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return str(self.name)

    class Meta:
        """Meta definition for Key."""

        db_table = "keys"
        verbose_name = "Key"
        verbose_name_plural = "Keys"
        ordering = ["name"]


class Pipeline(BaseModel):
    """Pipeline model"""

    id = models.UUIDField(primary_key=True, default=uuid4)
    github_url = models.URLField()

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return str(self.github_url)

    class Meta:
        """Meta definition for Pipeline."""

        db_table = "pipeline"
        verbose_name = "Pipeline"
        verbose_name_plural = "Pipelines"
        ordering = ["github_url"]


class Analysis(BaseModel):
    """Analysis model"""

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
        """Meta definition for Analysis."""

        db_table = "analysis"
        verbose_name = "Analysis"
        verbose_name_plural = "Analyses"
        ordering = ["name"]


class AnalysisType(BaseModel):
    """Analysis Type model"""

    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return str(self.name)

    class Meta:
        """Meta definition for AnalysisType."""

        db_table = "analysis_type"
        verbose_name = "Analysis Type"
        verbose_name_plural = "Analysis Types"
        ordering = ["name"]


class Tag(BaseModel):
    """Tag model"""

    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return str(self.slug)

    class Meta:
        """Meta definition for Tag."""

        db_table = "tag"
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ["slug"]


class Theme(BaseModel):
    """Theme model"""

    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return str(self.slug)

    class Meta:
        """Meta definition for Theme."""

        db_table = "theme"
        verbose_name = "Theme"
        verbose_name_plural = "Themes"
        ordering = ["slug"]


class Organization(BaseModel):
    """Organization model"""

    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=False, max_length=255)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    area = models.ForeignKey("Area", on_delete=models.CASCADE, related_name="organizations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    website = models.URLField(blank=True, null=True, max_length=255)
    twitter = models.URLField(blank=True, null=True)
    facebook = models.URLField(blank=True, null=True)
    linkedin = models.URLField(blank=True, null=True)
    instagram = models.URLField(blank=True, null=True)
    picture = models.ImageField(
        "Imagem",
        null=True,
        blank=True,
        storage=OverwriteStorage(),
        upload_to=upload_to,
        validators=[validate_image],
    )

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return str(self.slug)

    class Meta:
        """Meta definition for Organization."""

        db_table = "organization"
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"
        ordering = ["slug"]

    @property
    def full_slug(self):
        if self.area.slug != "unknown":
            return f"{self.area.slug}_{self.slug}"
        return f"{self.slug}"

    @property
    def has_picture(self):
        if self.picture and self.picture.url:
            return True
        return False


class Status(BaseModel):
    """Status model"""

    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)

    def __str__(self) -> str:
        return str(self.slug)

    graphql_nested_filter_fields_whitelist = ["id"]

    class Meta:
        """Meta class"""

        db_table = "status"
        verbose_name = "Status"
        verbose_name_plural = "Statuses"
        ordering = ["slug"]


class Dataset(BaseModel):
    """Dataset model"""

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
        help_text="Status is used to indicate at what stage of "
        "development or publishing the dataset is.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_closed = models.BooleanField(
        default=False, help_text="Dataset is for BD Pro subscribers only"
    )
    page_views = models.BigIntegerField(
        default=0,
        help_text="Number of page views by Google Analytics",
    )

    graphql_nested_filter_fields_whitelist = ["id", "slug"]

    def __str__(self):
        return str(self.slug)

    class Meta:
        """Meta class"""

        db_table = "dataset"
        verbose_name = "Dataset"
        verbose_name_plural = "Datasets"
        ordering = ["slug"]

    def get_success_url(self):
        """Get the success url for the dataset"""
        return reverse("datasetdetail", kwargs={"pk": self.object.pk})

    @property
    def full_slug(self):
        """Get the full slug or Dataset"""
        if self.organization.area.slug != "unknown":
            return f"{self.organization.area.slug}_{self.organization.slug}_{self.slug}"
        return f"{self.organization.slug}_{self.slug}"

    @property
    def coverage(self):
        """Get the temporal coverage of the dataset in the format YYYY-MM-DD - YYYY-MM-DD"""
        tables = self.tables.all()
        raw_data_sources = self.raw_data_sources.all()
        information_requests = self.information_requests.all()
        start_year, start_month, start_day = False, False, False
        end_year, end_month, end_day = False, False, False

        start_date = datetime(3000, 12, 31, 0, 0, 0)
        end_date = datetime(1, 1, 1, 0, 0, 0)

        # This must be refactored to avoid code duplication
        for table in tables:
            for coverage in table.coverages.all():
                date_times = DateTimeRange.objects.filter(coverage=coverage.pk)
                if len(date_times) == 0:
                    continue
                date_time = get_date_time(date_times)

                start_year = date_time.start_year if date_time.start_year else start_year
                start_month = date_time.start_month if date_time.start_month else start_month
                start_day = date_time.start_day if date_time.start_day else start_day
                end_year = date_time.end_year if date_time.end_year else end_year
                end_month = date_time.end_month if date_time.end_month else end_month
                end_day = date_time.end_day if date_time.end_day else end_day

                new_start_date = datetime(
                    date_time.start_year or 3000,
                    date_time.start_month or 1,
                    date_time.start_day or 1,
                )
                start_date = new_start_date if new_start_date < start_date else start_date
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

                start_year = date_time.start_year if date_time.start_year else start_year
                start_month = date_time.start_month if date_time.start_month else start_month
                start_day = date_time.start_day if date_time.start_day else start_day
                end_year = date_time.end_year if date_time.end_year else end_year
                end_month = date_time.end_month if date_time.end_month else end_month
                end_day = date_time.end_day if date_time.end_day else end_day

                new_start_date = datetime(
                    date_time.start_year or 3000,
                    date_time.start_month or 1,
                    date_time.start_day or 1,
                )
                start_date = new_start_date if new_start_date < start_date else start_date
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

                start_year = date_time.start_year if date_time.start_year else start_year
                start_month = date_time.start_month if date_time.start_month else start_month
                start_day = date_time.start_day if date_time.start_day else start_day
                end_year = date_time.end_year if date_time.end_year else end_year
                end_month = date_time.end_month if date_time.end_month else end_month
                end_day = date_time.end_day if date_time.end_day else end_day

                new_start_date = datetime(
                    date_time.start_year or 3000,
                    date_time.start_month or 1,
                    date_time.start_day or 1,
                )
                start_date = new_start_date if new_start_date < start_date else start_date
                new_end_date = datetime(
                    date_time.end_year or 1,
                    date_time.end_month or 1,
                    date_time.end_day or 1,
                )
                end_date = new_end_date if new_end_date > end_date else end_date

        start = []
        end = []

        if start_year and start_year < 3000 and start_date.year:
            start.append(str(start_date.year))
            if start_month and start_date.month:
                start.append(str(start_date.month).zfill(2))
                if start_day and start_date.day:
                    start.append(str(start_date.day).zfill(2))

        if end_year and end_year > 1 and end_date.year:
            end.append(str(end_date.year))
            if end_month and end_date.month:
                end.append(str(end_date.month).zfill(2))
                if end_day and end_date.day:
                    end.append(str(end_date.day).zfill(2))

        coverage_str = ""
        if start:
            coverage_str += "-".join(start)
        if end:
            coverage_str += " - " + "-".join(end)

        return coverage_str

    @property
    def full_coverage(self) -> str:
        """
        Returns the full temporal coverage of the dataset as a json string
        representing an object with the 3 initial points of the coverage
        The first point is the start of the open coverage, the second point is the
        end of the open coverage and the third point is the end of closed coverage
        When thera are only one type of coverage (open or closed) the second point
        will represent the end of the entire coverage, with both the types being
        the same

        Returns:
            str: json string representing the full coverage
        """
        full_coverage_dict = [
            # {"year": 2021, "month": 6, "type": "open"},
            # {"year": 2023, "month": 6, "type": "open"},
            # {"year": 2026, "month": 6, "type": "closed"},
        ]
        return json.dumps(full_coverage_dict)

    @property
    def contains_tables(self):
        """Returns true if there are tables in the dataset"""
        return len(self.tables.all()) > 0

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
    def contains_raw_data_sources(self):
        """Returns true if there are raw data sources in the dataset"""
        return len(self.raw_data_sources.all()) > 0

    @property
    def contains_information_requests(self):
        """Returns true if there are information requests in the dataset"""
        return len(self.information_requests.all()) > 0

    @property
    def table_last_updated_at(self):
        updates = [
            u.last_updated_at for u in self.tables.all()
            if u.last_updated_at
        ]  # fmt: skip
        return max(updates) if updates else None

    @property
    def raw_data_source_last_updated_at(self):
        updates = [
            u.last_updated_at for u in self.raw_data_sources.all()
            if u.last_updated_at
        ]  # fmt: skip
        return max(updates) if updates else None


class Update(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    entity = models.ForeignKey("Entity", on_delete=models.CASCADE, related_name="updates")
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
        """Meta definition for Update."""

        db_table = "update"
        verbose_name = "Update"
        verbose_name_plural = "Updates"
        ordering = ["frequency"]

    def clean(self) -> None:
        """Assert that only one of "table", "raw_data_source", "information_request" is set"""
        count = 0
        if self.table:
            count += 1
        if self.raw_data_source:
            count += 1
        if self.information_request:
            count += 1
        if count != 1:
            raise ValidationError(
                "One and only one of 'table', "
                "'raw_data_source', or 'information_request' must be set."
            )
        if self.entity.category.slug != "datetime":
            raise ValidationError("Entity's category is not in category.slug = `datetime`.")
        return super().clean()


class Table(BaseModel, OrderedModel):
    """Table model"""

    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=False, max_length=255)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    dataset = models.ForeignKey("Dataset", on_delete=models.CASCADE, related_name="tables")
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
    source_bucket_name = models.CharField(
        max_length=255, blank=True, null=True, default="basedosdados"
    )
    uncompressed_file_size = models.BigIntegerField(blank=True, null=True)
    compressed_file_size = models.BigIntegerField(blank=True, null=True)
    number_rows = models.BigIntegerField(blank=True, null=True)
    number_columns = models.BigIntegerField(blank=True, null=True)
    is_closed = models.BooleanField(default=False, help_text="Table is for BD Pro subscribers only")
    page_views = models.BigIntegerField(
        default=0,
        help_text="Number of page views by Google Analytics",
    )

    order_with_respect_to = ("dataset",)
    graphql_nested_filter_fields_whitelist = ["id", "dataset"]

    def __str__(self):
        return f"{str(self.dataset.slug)}.{str(self.slug)}"

    class Meta:
        """Meta definition for Table."""

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
    def gbq_slug(self):
        """Get the slug used in Google Big Query"""
        if cloud_table := self.cloud_tables.first():
            dataset = cloud_table.gcp_dataset_id
            table = cloud_table.gcp_table_id
            return f"basedosdados.{dataset}.{table}"

    @property
    def gcs_slug(self):
        """Get the slug used in Google Cloud Storage"""
        if cloud_table := self.cloud_tables.first():
            dataset = cloud_table.gcp_dataset_id
            table = cloud_table.gcp_table_id
            return f"staging/{dataset}/{table}"

    @property
    def partitions(self):
        """Returns a list of columns used to partition the table"""
        partitions_list = [p.name for p in self.columns.all().filter(is_partition=True)]
        return ", ".join(partitions_list)

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
    def full_coverage(self) -> str:
        """
        Returns the full temporal coverage of the table as a json string
        representing an object with the 3 initial points of the coverage
        The first point is the start of the open coverage, the second point is the
        end of the open coverage and the third point is the end of closed coverage
        When thera are only one type of coverage (open or closed) the second point
        will represent the end of the entire coverage, with both the types being
        the same

        Returns:
            str: json string representing the full coverage
        """
        # First area of all coverages - thus must be changed to get all areas
        try:
            first_area = self.coverages.first().area
        except AttributeError:
            return ""
        # First open coverage of a table - it's an open coverage for now
        try:
            first_open_datetime_range = (
                self.coverages.filter(area=first_area, is_closed=False)
                .first()
                .datetime_ranges.order_by("start_year", "start_month", "start_day")
                .first()
            )
        except AttributeError:
            first_open_datetime_range = None
        # First closed coverage of a table - it's a closed coverage for now
        try:
            first_closed_datetime_range = (
                self.coverages.filter(area=first_area, is_closed=True)
                .first()
                .datetime_ranges.order_by("start_year", "start_month", "start_day")
                .first()
            )
        except AttributeError:
            first_closed_datetime_range = None
        full_coverage = []
        if first_open_datetime_range:
            full_coverage.append(
                {
                    "year": to_str(first_open_datetime_range.start_year),
                    "month": to_str(first_open_datetime_range.start_month, 2),
                    "day": to_str(first_open_datetime_range.start_day, 2),
                    "type": "open",
                }
            )
            full_coverage.append(
                {
                    "year": to_str(first_open_datetime_range.end_year, 2),
                    "month": to_str(first_open_datetime_range.end_month, 2),
                    "day": to_str(first_open_datetime_range.end_day, 2),
                    "type": "open",
                }
            )
        if first_closed_datetime_range:
            if not first_open_datetime_range:
                full_coverage.append(
                    {
                        "year": to_str(first_closed_datetime_range.start_year),
                        "month": to_str(first_closed_datetime_range.start_month, 2),
                        "day": to_str(first_closed_datetime_range.start_day, 2),
                        "type": "closed",
                    }
                )
            full_coverage.append(
                {
                    "year": to_str(first_closed_datetime_range.end_year),
                    "month": to_str(first_closed_datetime_range.end_month, 2),
                    "day": to_str(first_closed_datetime_range.end_day, 2),
                    "type": "closed",
                }
            )

        return json.dumps(full_coverage)

    @property
    def neighbors(self) -> list[dict]:
        """Similiar tables and columns
        - Tables and columns with similar directories
        - Tables and columns with similar coverages or tags
        """
        all_tables = (
            Table.objects.exclude(id=self.id)
            .exclude(is_directory=True)
            .exclude(status__slug__in=["under_review"])
            .filter(columns__directory_primary_key__isnull=False)
            .distinct()
            .all()
        )
        all_neighbors = []
        for table in all_tables:
            score_area = self.get_similarity_of_area(table)
            score_datetime = self.get_similarity_of_datetime(table)
            score_directory, columns = self.get_similarity_of_directory(table)
            if not score_directory:
                continue
            column_id = []
            column_name = []
            for column in columns:
                column_id.append(str(column.id))
                column_name.append(column.name)
            all_neighbors.append(
                {
                    "column_id": column_id,
                    "column_name": column_name,
                    "table_id": str(table.id),
                    "table_name": table.name,
                    "dataset_id": str(table.dataset.id),
                    "dataset_name": table.dataset.name,
                    "score": round(score_area + score_datetime + score_directory, 2),
                }
            )
        return sorted(all_neighbors, key=lambda item: item["score"])[::-1][:20]

    @property
    def last_updated_at(self):
        updates = [u.latest for u in self.updates.all() if u.latest]
        return max(updates) if updates else None

    def get_similarity_of_area(self, other: "Table"):
        count_all = 0
        count_yes = 0
        for cov_self in self.coverages.all():
            for cov_other in other.coverages.all():
                count_all += 1
                count_yes += cov_self.get_similarity_of_area(cov_other)
        return count_yes / count_all if count_all else 0

    def get_similarity_of_datetime(self, other: "Table"):
        count_all = 0
        count_yes = 0
        for cov_self in self.coverages.all():
            for cov_other in other.coverages.all():
                count_all += 1
                count_yes += cov_self.get_similarity_of_datetime(cov_other)
        return count_yes / count_all if count_all else 0

    def get_similarity_of_directory(self, other: "Table"):
        self_cols = self.columns.all()
        self_dirs = self.columns.filter(directory_primary_key__isnull=False).all()
        other_cols = other.columns.all()
        other_dirs = other.columns.filter(directory_primary_key__isnull=False).all()
        intersection = set([*self_dirs, *other_dirs])
        intersection_size = len(intersection)
        intersection_max_size = min(len(self_cols), len(other_cols))
        return intersection_size / intersection_max_size, intersection

    def clean(self):
        """
        Clean method for Table model
            - Coverages must not overlap
        """
        errors = {}
        try:
            temporal_coverages_by_area = defaultdict(lambda: [])
            for coverage in self.coverages.all():
                if area := coverage.area:
                    try:
                        temporal_coverages_by_area[str(area.slug)].append(
                            *list(coverage.datetime_ranges.all())
                        )
                    except TypeError:
                        continue
            for area, temporal_coverages in temporal_coverages_by_area.items():
                datetime_ranges = []
                for temporal_coverage in temporal_coverages:
                    datetime_ranges.append(
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
                datetime_ranges.sort(key=lambda x: x[0])
                for i in range(1, len(datetime_ranges)):
                    if datetime_ranges[i - 1][1] > datetime_ranges[i][0]:
                        errors = f"Temporal coverages in area {area} overlap"
        except ValueError:
            pass

        if errors:
            raise ValidationError(errors)


class BigQueryType(BaseModel):
    """Model definition for BigQueryType."""

    id = models.UUIDField(primary_key=True, default=uuid4)
    name = models.CharField(max_length=255)

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return str(self.name)

    class Meta:
        """Meta definition for BigQueryType."""

        db_table = "bigquery_type"
        verbose_name = "BigQuery Type"
        verbose_name_plural = "BigQuery Types"
        ordering = ["name"]


class Column(BaseModel, OrderedModel):
    """Model definition for Column."""

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
        """Meta definition for Column."""

        db_table = "column"
        verbose_name = "Column"
        verbose_name_plural = "Columns"
        ordering = ["name"]

    @property
    def full_coverage(self) -> str:
        """
        Returns the coverage of the column if it exists,
        otherwise returns the coverage of the table
        Currently returns the first coverage, but this
        should be changed to return the
        full coverage of the column, as in table coverage

        Returns:
            str: coverage of the column - a dumped list of dicts [start_date, end_date]
        """

        coverages = self.coverages.all()
        column_full_coverage = []

        if (
            len(coverages) == 0
            or not coverages[0].datetime_ranges.exists()
            or coverages[0].datetime_ranges.first().start_year is None
        ):
            """
            At the moment, only one coverage exists per column
            No coverage for column, using table coverage
            """
            table_full_coverage = json.loads(self.table.full_coverage)
            temporal_coverage_start = table_full_coverage[0]
            temporal_coverage_end = table_full_coverage[-1]
        elif coverages[0].datetime_ranges.first().start_year is not None:
            dt_range = coverages[0].datetime_ranges.first()
            temporal_coverage_start = {
                "year": to_str(dt_range.start_year),
                "month": to_str(dt_range.start_month, 2),
                "day": to_str(dt_range.start_day, 2),
            }
            temporal_coverage_end = {
                "year": to_str(dt_range.end_year),
                "month": to_str(dt_range.end_month, 2),
                "day": to_str(dt_range.end_day, 2),
            }
        else:
            temporal_coverage_start = {"year": "", "month": "", "day": ""}
            temporal_coverage_end = {"year": "", "month": "", "day": ""}

        column_full_coverage.append(temporal_coverage_start)
        column_full_coverage.append(temporal_coverage_end)

        return json.dumps(column_full_coverage)

    def clean(self) -> None:
        """Clean method for Column model"""
        errors = {}
        if self.observation_level and self.observation_level.table != self.table:
            errors[
                "observation_level"
            ] = "Observation level is not in the same table as the column."
        if self.directory_primary_key and self.directory_primary_key.table.is_directory is False:
            errors[
                "directory_primary_key"
            ] = "Column indicated as a directory's primary key is not in a directory."
        if errors:
            raise ValidationError(errors)
        return super().clean()


class ColumnOriginalName(BaseModel):
    """Model definition for ColumnOriginalName."""

    id = models.UUIDField(primary_key=True, default=uuid4)
    column = models.ForeignKey(
        "Column", on_delete=models.CASCADE, related_name="column_original_names"
    )
    name = models.CharField(max_length=255)

    graphql_nested_filter_fields_whitelist = ["id", "name"]

    def __str__(self):
        return (
            f"{self.column.table.dataset.slug}."
            f"{self.column.table.slug}.{self.column.name}.{self.name}"
        )

    class Meta:
        """Meta definition for ColumnOriginalName."""

        db_table = "column_original_name"
        verbose_name = "Column Original Name"
        verbose_name_plural = "Column Original Names"


class Dictionary(BaseModel):
    """Model definition for Dictionary."""

    id = models.UUIDField(primary_key=True, default=uuid4)
    column = models.ForeignKey("Column", on_delete=models.CASCADE, related_name="dictionaries")

    graphql_nested_filter_fields_whitelist = ["id"]

    class Meta:
        """Meta definition for Dictionary."""

        verbose_name = "Dictionary"
        verbose_name_plural = "Dictionaries"
        ordering = ["column"]

    def __str__(self):
        return f"{self.column.table.dataset.slug}.{self.column.table.slug}.{self.column.name}"


class CloudTable(BaseModel):
    """Model definition for CloudTable."""

    id = models.UUIDField(primary_key=True, default=uuid4)
    table = models.ForeignKey("Table", on_delete=models.CASCADE, related_name="cloud_tables")
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
                errors["columns"] = f"Column {column} does not belong to table {self.table}."
        if errors:
            raise ValidationError(errors)

        return super().clean()

    class Meta:
        """Meta definition for CloudTable."""

        db_table = "cloud_table"
        verbose_name = "Cloud Table"
        verbose_name_plural = "Cloud Tables"
        ordering = ["id"]


class Availability(BaseModel):
    """Model definition for Availability."""

    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return str(self.slug)

    class Meta:
        """Meta definition for Availability."""

        db_table = "availability"
        verbose_name = "Availability"
        verbose_name_plural = "Availabilities"
        ordering = ["slug"]


class Language(BaseModel):
    """Model definition for Language."""

    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return str(self.slug)

    class Meta:
        """Meta definition for Language."""

        db_table = "language"
        verbose_name = "Language"
        verbose_name_plural = "Languages"
        ordering = ["slug"]


class RawDataSource(BaseModel, OrderedModel):
    """Model definition for RawDataSource."""

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
    languages = models.ManyToManyField("Language", related_name="raw_data_sources", blank=True)
    license = models.ForeignKey(
        "License",
        on_delete=models.CASCADE,
        related_name="raw_data_sources",
        blank=True,
        null=True,
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
        """Meta definition for RawDataSource."""

        db_table = "raw_data_source"
        verbose_name = "Raw Data Source"
        verbose_name_plural = "Raw Data Sources"
        ordering = ["url"]

    def __str__(self):
        return f"{self.name} ({self.dataset.name})"

    @property
    def last_updated_at(self):
        updates = [u.latest for u in self.updates.all() if u.latest]
        return max(updates) if updates else None


class InformationRequest(BaseModel, OrderedModel):
    """Model definition for InformationRequest."""

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
        """Meta definition for InformationRequest."""

        db_table = "information_request"
        verbose_name = "Information Request"
        verbose_name_plural = "Information Requests"
        ordering = ["number"]

    def clean(self) -> None:
        """Validate the model fields."""
        errors = {}
        if self.origin is not None and len(self.origin) > 500:
            errors["origin"] = "Origin cannot be longer than 500 characters"
        if errors:
            raise ValidationError(errors)

        return super().clean()


class EntityCategory(BaseModel):
    """Model definition for Entity Category."""

    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return str(self.slug)

    class Meta:
        """Meta definition for Entity Category."""

        db_table = "entity_category"
        verbose_name = "Entity Category"
        verbose_name_plural = "Entity Categories"
        ordering = ["slug"]


class Entity(BaseModel):
    """Model definition for Entity."""

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
        """Meta definition for Entity."""

        db_table = "entity"
        verbose_name = "Entity"
        verbose_name_plural = "Entities"
        ordering = ["slug"]


class ObservationLevel(BaseModel):
    """Model definition for ObservationLevel."""

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
        """Meta definition for ObservationLevel."""

        db_table = "observation_level"
        verbose_name = "Observation Level"
        verbose_name_plural = "Observation Levels"
        ordering = ["id"]

    def clean(self) -> None:
        """Assert that only one of "table", "raw_data_source", "information_request" is set"""
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
                "One and only one of 'table', 'raw_data_source', "
                "'information_request', 'analysis' must be set."
            )
        return super().clean()


class DateTimeRange(BaseModel):
    """Model definition for DateTimeRange."""

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
    is_closed = models.BooleanField("Is Closed", default=False)

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return f"{self.since_str}({self.interval_str}){self.until_str}"

    class Meta:
        """Meta definition for DateTimeRange."""

        db_table = "datetime_range"
        verbose_name = "DateTime Range"
        verbose_name_plural = "DateTime Ranges"
        ordering = ["id"]

    @property
    def since(self):
        if self.start_year:
            return datetime(
                self.start_year,
                self.start_month or 1,
                self.start_day or 1,
                self.start_hour or 0,
                self.start_minute or 0,
                self.start_second or 0,
            )

    @property
    def since_str(self):
        if self.start_year and self.start_month and self.start_day:
            return self.since.strftime("%Y-%m-%d")
        if self.start_year and self.start_month:
            return self.since.strftime("%Y-%m")
        if self.start_year:
            return self.since.strftime("%Y")
        return ""

    @property
    def until(self):
        if self.end_year:
            return datetime(
                self.end_year,
                self.end_month or 1,
                self.end_day or 1,
                self.end_hour or 0,
                self.end_minute or 0,
                self.end_second or 0,
            )

    @property
    def until_str(self):
        if self.end_year and self.end_month and self.end_day:
            return self.until.strftime("%Y-%m-%d")
        if self.end_year and self.end_month:
            return self.until.strftime("%Y-%m")
        if self.end_year:
            return self.until.strftime("%Y")
        return ""

    @property
    def interval_str(self):
        if self.interval:
            return str(self.interval)
        return "0"

    def get_similarity_of_datetime(self, other: "DateTimeRange"):
        if not self.since:
            return 0
        if not other.until:
            return 0
        if self.since <= other.until:
            return 1
        if self.until >= other.since:
            return 1
        return 0

    def clean(self) -> None:
        """
        Assert that start_year <= end_year and start_month <= end_month
        and start_day <= end_day
        """
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
                    errors["start_year"] = ["Start datetime cannot be greater than end datetime"]

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


class QualityCheck(BaseModel):
    """Model definition for QualityCheck."""

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
        """Meta definition for QualityCheck."""

        db_table = "quality_check"
        verbose_name = "Quality Check"
        verbose_name_plural = "Quality Checks"
        ordering = ["id"]

    def clean(self) -> None:
        """Validate that only one of the FKs is set."""
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
                "One and only one of 'analysis', 'dataset, 'table', "
                "'column', 'key, 'raw_data_source', 'information_request' must be set."
            )
        return super().clean()
