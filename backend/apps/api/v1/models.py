# -*- coding: utf-8 -*-
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from math import log10
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models
from ordered_model.models import OrderedModel

from backend.apps.account.models import Account
from backend.custom.model import BaseModel
from backend.custom.storage import OverwriteStorage, upload_to, validate_image
from backend.custom.utils import check_kebab_case, check_snake_case

import logging

logger = logging.getLogger('django.request')

class Area(BaseModel):
    """Area model"""

    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255, blank=False, null=False)
    administrative_level = models.IntegerField(
        null=True, 
        blank=True,
        choices=[
            (0, '0'),
            (1, '1'),
            (2, '2'),
            (3, '3'),
            (4, '4'),
            (5, '5'),
        ]
    )
    entity = models.ForeignKey(
        "Entity",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="areas",
        limit_choices_to={'category__slug': 'spatial'}
    )
    parent = models.ForeignKey(
        "Area",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return f"{str(self.name)} ({str(self.slug)})"

    class Meta:
        """Meta definition for Area."""

        db_table = "area"
        verbose_name = "Area"
        verbose_name_plural = "Areas"
        ordering = ["name"]

    def clean(self):
        """Validate the model fields."""
        errors = {}
        if self.administrative_level is not None and self.administrative_level not in [0, 1, 2, 3]:
            errors['administrative_level'] = 'Administrative level must be 0, 1, 2, or 3'
        
        if self.entity and self.entity.category.slug != 'spatial':
            errors['entity'] = 'Entity must have category "spatial"'
        
        if self.parent and self.parent.slug != 'world':
            if self.administrative_level is None:
                errors['administrative_level'] = 'Administrative level is required when parent is set'
            elif self.parent.administrative_level is None:
                errors['parent'] = 'Parent must have an administrative level'
            elif self.parent.administrative_level != self.administrative_level - 1:
                errors['parent'] = 'Parent must have administrative level exactly one level above'
        
        if errors:
            raise ValidationError(errors)
        return super().clean()


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
        on_delete=models.SET_NULL,
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
        "AnalysisType",
        on_delete=models.SET_NULL,
        null=True,
        related_name="analyses",
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
    area = models.ForeignKey("Area", on_delete=models.SET_NULL, null=True, related_name="organizations")
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
    organizations = models.ManyToManyField(
        "Organization",
        related_name="datasets",
        verbose_name="Organizations",
        help_text="Organizations associated with this dataset"
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

    @property
    def full_slug(self):
        if self.organizations.first().area.slug != "unknown":
            return f"{self.organizations.first().area.slug}_{self.slug}"
        return f"{self.slug}"

    @property
    def popularity(self):
        if not self.page_views:
            return 0.0
        if self.page_views < 1:
            return 0.0
        return log10(self.page_views)

    @property
    def temporal_coverage(self) -> dict:
        """Temporal coverage of all related entities"""
        resources = [
            *self.tables.all(),
            *self.raw_data_sources.all(),
            *self.information_requests.all(),
        ]
        temporal_coverage = get_temporal_coverage(resources)
        if temporal_coverage["start"] and temporal_coverage["end"]:
            return f"{temporal_coverage['start']} - {temporal_coverage['end']}"
        if temporal_coverage["start"]:
            return f"{temporal_coverage['start']}"
        if temporal_coverage["end"]:
            return f"{temporal_coverage['end']}"
        return ""

    @property
    def spatial_coverage(self) -> list[str]:
        """Union spatial coverage of all related resources"""
        resources = [
            *self.tables.all(),
            *self.raw_data_sources.all(),
            *self.information_requests.all(),
        ]
        return sorted(list(get_spatial_coverage(resources)))

    @property
    def entities(self) -> list[dict]:
        """Entity of all related resources"""
        entities = []
        resources = [
            *self.tables.all(),
            *self.raw_data_sources.all(),
            *self.information_requests.all(),
        ]
        for resource in resources:
            for observation in resource.observation_levels.all():
                entities.append(observation.entity.as_search_result)
        return entities

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
    def contains_tables(self):
        """Returns true if there are tables in the dataset"""
        return len(self.tables.all()) > 0

    @property
    def contains_raw_data_sources(self):
        """Returns true if there are raw data sources in the dataset"""
        return len(self.raw_data_sources.all()) > 0

    @property
    def contains_information_requests(self):
        """Returns true if there are information requests in the dataset"""
        return len(self.information_requests.all()) > 0

    @property
    def n_tables(self):
        return len(self.tables.exclude(status__slug="under_review").all())

    @property
    def n_raw_data_sources(self):
        return len(self.raw_data_sources.exclude(status__slug="under_review").all())

    @property
    def n_information_requests(self):
        return len(self.information_requests.exclude(status__slug="under_review").all())

    @property
    def first_table_id(self):
        if resource := self.tables.exclude(status__slug="under_review").order_by("order").first():
            return resource.pk

    @property
    def first_open_table_id(self):
        for resource in self.tables.exclude(status__slug="under_review").order_by("order").all():
            if resource.contains_open_data:
                return resource.pk

    @property
    def first_closed_table_id(self):
        for resource in self.tables.exclude(status__slug="under_review").order_by("order").all():
            if resource.contains_closed_data:
                return resource.pk

    @property
    def first_raw_data_source_id(self):
        resource = (
            self.raw_data_sources
            .exclude(status__slug="under_review")
            .order_by("order")
            .first()
        )  # fmt: skip
        return resource.pk if resource else None

    @property
    def first_information_request_id(self):
        resource = (
            self.information_requests
            .exclude(status__slug="under_review")
            .order_by("order")
            .first()
        )  # fmt: skip
        return resource.pk if resource else None

    @property
    def table_last_updated_at(self):
        updates = [
            u.last_updated_at for u in self.tables.all()
            if u.last_updated_at
        ]  # fmt: skip
        return max(updates) if updates else None

    @property
    def raw_data_source_last_polled_at(self):
        polls = [
            u.last_polled_at for u in self.raw_data_sources.all()
            if u.last_polled_at
        ]  # fmt: skip
        return max(polls) if polls else None

    @property
    def raw_data_source_last_updated_at(self):
        updates = [
            u.last_updated_at for u in self.raw_data_sources.all()
            if u.last_updated_at
        ]  # fmt: skip
        return max(updates) if updates else None


class Update(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    entity = models.ForeignKey(
        "Entity",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="updates",
        limit_choices_to={'category__slug': 'datetime'}
    )
    frequency = models.IntegerField(blank=True, null=True)
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
        errors = {}
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
        if self.entity and self.entity.category.slug != 'datetime':
            errors['entity'] = 'Entity must have category "datetime"'
        if errors:
            raise ValidationError(errors)
        return super().clean()


class Poll(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    entity = models.ForeignKey(
        "Entity",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="polls",
        limit_choices_to={'category__slug': 'datetime'}
    )
    frequency = models.IntegerField(blank=True, null=True)
    latest = models.DateTimeField(blank=True, null=True)
    pipeline = models.ForeignKey(
        "Pipeline",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="polls",
    )
    raw_data_source = models.ForeignKey(
        "RawDataSource",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="polls",
    )
    information_request = models.ForeignKey(
        "InformationRequest",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="polls",
    )

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return f"{str(self.frequency)} {str(self.entity)}"

    class Meta:
        """Meta definition for Poll."""

        db_table = "poll"
        verbose_name = "Poll"
        verbose_name_plural = "Polls"
        ordering = ["frequency"]

    def clean(self) -> None:
        """Assert that only one of "raw_data_source", "information_request" is set"""
        errors = {}
        if bool(self.raw_data_source) == bool(self.information_request):
            raise ValidationError(
                "One and only one of 'raw_data_source'," " or 'information_request' must be set."
            )
        if self.entity and self.entity.category.slug != 'datetime':
            errors['entity'] = 'Entity must have category "datetime"'
        if errors:
            raise ValidationError(errors)
        return super().clean()


class Table(BaseModel, OrderedModel):
    """Table model"""

    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=False, max_length=255)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    dataset = models.ForeignKey("Dataset", on_delete=models.CASCADE, related_name="tables")
    raw_data_source = models.ManyToManyField(
        "RawDataSource",
        related_name="tables",
        blank=True,
    )
    version = models.IntegerField(null=True, blank=True)
    status = models.ForeignKey(
        "Status", on_delete=models.PROTECT, related_name="tables", null=True, blank=True
    )
    license = models.ForeignKey(
        "License",
        on_delete=models.SET_NULL,
        related_name="tables",
        blank=True,
        null=True,
    )
    partner_organization = models.ForeignKey(
        "Organization",
        on_delete=models.SET_NULL,
        related_name="partner_tables",
        blank=True,
        null=True,
    )
    pipeline = models.ForeignKey(
        "Pipeline",
        on_delete=models.SET_NULL,
        related_name="tables",
        blank=True,
        null=True,
    )
    is_directory = models.BooleanField(default=False, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_by = models.ManyToManyField(
        Account,
        related_name="tables_published",
        blank=True,
        verbose_name="Published by",
        help_text="People who published the table",
    )
    data_cleaned_by = models.ManyToManyField(
        Account,
        related_name="tables_cleaned",
        blank=True,
        verbose_name="Data cleaned by",
        help_text="People who cleaned the data",
    )
    data_cleaning_description = models.TextField(blank=True, null=True)
    data_cleaning_code_url = models.URLField(blank=True, null=True)
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
    def full_slug(self):
        return self.slug

    @property
    def gbq_slug(self):
        """Get the slug used in Google Big Query"""
        if cloud_table := self.cloud_tables.first():
            dataset = cloud_table.gcp_dataset_id
            table = cloud_table.gcp_table_id
            return f"basedosdados.{dataset}.{table}"

    @property
    def gbq_dict_slug(self):
        """Get the dictionary slug used in Google Big Query"""
        if cloud_table := self.cloud_tables.first():
            dataset = cloud_table.gcp_dataset_id
            return f"basedosdados.{dataset}.dicionario"

    @property
    def gbq_table_slug(self):
        """Get the table slug used in Google Big Query"""
        if cloud_table := self.cloud_tables.first():
            return cloud_table.gcp_table_id

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
    def contains_open_data(self):
        if self.coverages.filter(is_closed=False):
            return True
        for column in self.columns.all():
            if column.coverages.filter(is_closed=False).first():
                return True
        return False

    @property
    def contains_closed_data(self):
        if self.coverages.filter(is_closed=True).first():
            return True
        for column in self.columns.all():
            if column.coverages.filter(is_closed=True).first():
                return True
        return False

    @property
    def temporal_coverage(self) -> dict:
        """Temporal coverage"""
        return get_temporal_coverage([self])

    @property
    def full_temporal_coverage(self) -> dict:
        """Temporal coverage steps"""
        return get_full_temporal_coverage([self])

    @property
    def spatial_coverage(self) -> list[str]:
        """Unique list of areas across all coverages"""
        return sorted(list(get_spatial_coverage([self])))

    @property
    def neighbors(self) -> list[dict]:
        """Similiar tables and columns without filters"""
        all_neighbors = [t.as_dict for t in TableNeighbor.objects.filter(table_a=self)]
        all_neighbors = sorted(all_neighbors, key=lambda item: item["score"], reverse=True)
        return all_neighbors

    @property
    def last_updated_at(self):
        updates = [u.latest for u in self.updates.all() if u.latest]
        return max(updates) if updates else None

    @property
    def published_by_info(self) -> list[dict]:
        """Return list of author information"""
        if not self.published_by.exists():
            return []
        return [
            {
                "firstName": author.first_name,
                "lastName": author.last_name,
                "email": author.email,
                "github": author.github,
                "twitter": author.twitter,
                "website": author.website,
            }
            for author in self.published_by.all()
        ]

    @property
    def data_cleaned_by_info(self) -> list[dict]:
        """Return list of data cleaner information"""
        if not self.data_cleaned_by.exists():
            return []
        return [
            {
                "firstName": cleaner.first_name,
                "lastName": cleaner.last_name,
                "email": cleaner.email,
                "github": cleaner.github,
                "twitter": cleaner.twitter,
                "website": cleaner.website,
            }
            for cleaner in self.data_cleaned_by.all()
        ]

    @property
    def coverage_datetime_units(self) -> str:
        units = []
        for coverage in self.coverages.all():
            for datetime_range in coverage.datetime_ranges.all():
                units.extend([unit.name for unit in datetime_range.units.all()])
        
        if not units:
            return None
        
        most_common_unit = list(set(units))
        return most_common_unit

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
        self_columns = (
            self.columns
            .filter(directory_primary_key__isnull=False)
            .exclude(directory_primary_key__table__dataset__slug="diretorios_data_tempo")
            .all()
        )  # fmt: skip
        self_directories = set(c.directory_primary_key for c in self_columns)
        other_columns = (
            other.columns
            .filter(directory_primary_key__isnull=False)
            .exclude(directory_primary_key__table__dataset__slug="diretorios_data_tempo")
            .all()
        )  # fmt: skip
        other_directories = set(c.directory_primary_key for c in other_columns)
        intersection = self_directories.intersection(other_directories)
        return len(intersection) / len(self_directories), intersection

    def gen_neighbors(self) -> list[dict]:
        self_columns = (
            self.columns
            .filter(directory_primary_key__isnull=False)
            .exclude(directory_primary_key__table__dataset__slug="diretorios_data_tempo")
            .all()
        )  # fmt: skip
        self_directories = set(c.directory_primary_key for c in self_columns)
        if not self_directories:
            return []
        all_tables = (
            Table.objects
            .exclude(id=self.id)
            .exclude(is_directory=True)
            .exclude(status__slug__in=["under_review"])
            .filter(columns__directory_primary_key__isnull=False)
            .distinct()
            .all()
        )  # fmt: skip
        all_neighbors = []
        for table in all_tables:
            similarity_of_area = self.get_similarity_of_area(table)
            similarity_of_datetime = self.get_similarity_of_datetime(table)
            similarity_of_directory, columns = self.get_similarity_of_directory(table)
            similarity_of_popularity = table.dataset.popularity
            if not similarity_of_area or not similarity_of_datetime or not similarity_of_directory:
                continue
            all_neighbors.append(
                {
                    "table_a": self,
                    "table_b": table,
                    "similarity_of_area": similarity_of_area,
                    "similarity_of_datetime": similarity_of_datetime,
                    "similarity_of_directory": similarity_of_directory,
                    "similarity_of_popularity": similarity_of_popularity,
                }
            )
        return all_neighbors

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
                        errors['coverages_areas'] = f"Temporal coverages in area {area} overlap"
        except ValueError:
            pass
        
        if errors:
            raise ValidationError(errors)
        return super().clean()


class TableNeighbor(BaseModel):
    table_a = models.ForeignKey(
        Table,
        on_delete=models.DO_NOTHING,
        related_name="tableneighbor_a_set",
    )
    table_b = models.ForeignKey(
        Table,
        on_delete=models.DO_NOTHING,
        related_name="tableneighbor_b_set",
    )

    similarity = models.FloatField(default=0)
    similarity_of_area = models.FloatField(default=0)
    similarity_of_datetime = models.FloatField(default=0)
    similarity_of_directory = models.FloatField(default=0)
    similarity_of_popularity = models.FloatField(default=0)

    class Meta:
        db_table = "table_neighbor"
        constraints = [
            models.UniqueConstraint(
                fields=["table_a", "table_b"],
                name="table_neighbor_unique_constraint",
            ),
        ]

    @property
    def score(self):
        return round(self.similarity_of_directory, 2) + round(self.similarity_of_popularity, 2)

    @property
    def as_dict(self):
        return {
            "table_id": str(self.table_b.pk),
            "table_name": self.table_b.name,
            "dataset_id": str(self.table_b.dataset.pk),
            "dataset_name": self.table_b.dataset.name,
            "score": self.score,
        }

    def clean(self) -> None:
        errors = {}
        if self.table_a.pk == self.table_b.pk:
            errors["table_a"] = "Table neighbors A & B shouldn't be the same"
            errors["table_b"] = "Table neighbors A & B shouldn't be the same"
        if errors:
            raise ValidationError(errors)
        return super().clean()


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

class MeasurementUnitCategory(BaseModel):
    """Model definition for MeasurementUnitCategory."""

    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)
    
    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return str(self.slug)

    class Meta:
        """Meta definition for Measurement Unit Category."""

        db_table = "measurement_unit_category"
        verbose_name = "Measurement Unit Category"
        verbose_name_plural = "Measurement Unit Categories"
        ordering = ["slug"]

class MeasurementUnit(BaseModel):
    """Model definition for MeasurementUnit."""

    id = models.UUIDField(primary_key=True, default=uuid4)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)
    tex = models.CharField(max_length=255, blank=True, null=True)
    category = models.ForeignKey(
        "MeasurementUnitCategory",
        on_delete=models.SET_NULL,
        null=True,
        related_name="measurement_units",
    )

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return str(self.slug)

    class Meta:
        """Meta definition for MeasurementUnit."""

        db_table = "measurement_unit"
        verbose_name = "Measurement Unit"
        verbose_name_plural = "Measurement Units"
        ordering = ["slug"]

class Column(BaseModel, OrderedModel):
    """Model definition for Column."""

    id = models.UUIDField(primary_key=True, default=uuid4)
    table = models.ForeignKey("Table", on_delete=models.CASCADE, related_name="columns")
    name = models.CharField(max_length=255)
    name_staging = models.CharField(max_length=255, blank=True, null=True)
    bigquery_type = models.ForeignKey(
        "BigQueryType", on_delete=models.SET_NULL, null=True, related_name="columns"
    )
    description = models.TextField(blank=True, null=True)
    covered_by_dictionary = models.BooleanField(default=False, blank=True, null=True)
    is_primary_key = models.BooleanField(default=False, blank=True, null=True)
    directory_primary_key = models.ForeignKey(
        "Column",
        on_delete=models.SET_NULL,
        null=True,
        related_name="columns",
        blank=True,
        limit_choices_to={'is_primary_key': True, 'table__is_directory': True}
    )
    measurement_unit = models.CharField(max_length=255, blank=True, null=True)
    contains_sensitive_data = models.BooleanField(default=False, blank=True, null=True)
    observations = models.TextField(blank=True, null=True)
    is_in_staging = models.BooleanField(default=True)
    is_partition = models.BooleanField(default=False)
    observation_level = models.ForeignKey(
        "ObservationLevel",
        on_delete=models.SET_NULL,
        null=True,
        related_name="columns",
        blank=True,
    )
    version = models.IntegerField(null=True, blank=True)
    status = models.ForeignKey(
        "Status",
        on_delete=models.SET_NULL,
        null=True,
        related_name="columns",
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
    def temporal_coverage(self) -> dict:
        """Temporal coverage of column if exists, if not table coverage"""
        temporal_coverage = get_temporal_coverage([self])
        fallback = defaultdict(lambda: None)
        if not temporal_coverage["start"] or not temporal_coverage["end"]:
            fallback = self.table.temporal_coverage
        return {
            "start": temporal_coverage["start"] or fallback["start"],
            "end": temporal_coverage["end"] or fallback["end"],
        }

    @property
    def spatial_coverage(self) -> list[str]:
        """Unique list of areas across all coverages, falling back to table coverage if empty"""
        coverage = get_spatial_coverage([self])
        if not coverage:
            return get_spatial_coverage([self.table])
        return coverage

    @property
    def dir_column(self):
        """Column of directory table and column"""
        if self.directory_primary_key:
            return self.directory_primary_key

    @property
    def dir_cloud_table(self):
        """Cloud table of directory table and column"""
        if dir_column := self.directory_primary_key:
            if cloud_table := dir_column.cloud_tables.first():
                return cloud_table

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

    @property
    def gcp_prefix_id(self):
        return f"{self.gcp_project_id}.{self.gcp_dataset_id}"

    @property
    def gcp_suffix_id(self):
        return f"{self.gcp_dataset_id}.{self.gcp_table_id}"

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
        "Availability", on_delete=models.SET_NULL, null=True, related_name="raw_data_sources"
    )
    languages = models.ManyToManyField("Language", related_name="raw_data_sources", blank=True)
    license = models.ForeignKey(
        "License",
        on_delete=models.SET_NULL,
        null=True,
        related_name="raw_data_sources",
        blank=True,
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
    def last_polled_at(self):
        polls = [u.latest for u in self.polls.all() if u.latest]
        return max(polls) if polls else None

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
        on_delete=models.SET_NULL,
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
        "EntityCategory", on_delete=models.SET_NULL, null=True, related_name="entities"
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


class ObservationLevel(BaseModel, OrderedModel):
    """Model definition for ObservationLevel."""

    id = models.UUIDField(primary_key=True, default=uuid4)
    entity = models.ForeignKey(
        "Entity", on_delete=models.SET_NULL, null=True, related_name="observation_levels"
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

    order_with_respect_to = ('table', 'raw_data_source', 'information_request', 'analysis')

    graphql_nested_filter_fields_whitelist = ["id"]

    def __str__(self):
        return str(self.entity)

    class Meta:
        """Meta definition for ObservationLevel."""

        db_table = "observation_level"
        verbose_name = "Observation Level"
        verbose_name_plural = "Observation Levels"
        ordering = ["order"]

    def get_ordering_queryset(self):
        """Get queryset for ordering within the appropriate parent"""
        qs = super().get_ordering_queryset()
        
        # Filter by the appropriate parent field
        if self.table_id:
            return qs.filter(table_id=self.table_id)
        elif self.raw_data_source_id:
            return qs.filter(raw_data_source_id=self.raw_data_source_id)
        elif self.information_request_id:
            return qs.filter(information_request_id=self.information_request_id)
        elif self.analysis_id:
            return qs.filter(analysis_id=self.analysis_id)
        
        return qs


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
    units = models.ManyToManyField(
        "Column",
        related_name="datetime_ranges",
        blank=True,
    )
    is_closed = models.BooleanField("Is Closed", default=False)

    graphql_fields_blacklist = BaseModel.graphql_fields_blacklist + ["since", "until"]
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

    def clean(self):
        errors = {}
        try:
            if self.since and self.until and self.since > self.until:
                errors['date_range'] = "Start date must be less than or equal to end date"
            if self.since and self.until and not self.interval:
                errors['interval'] = "Interval must exist in ranges with start and end dates"
            
            # Add validation for units
            #for unit in self.units.all():
            #    if unit.bigquery_type.name not in ['DATE', 'DATETIME', 'TIME', 'TIMESTAMP']:
            #        errors['units'] = f"Column '{unit.name}' is not a valid datetime unit"
        except Exception as e:
            errors['general'] = f"An error occurred: {str(e)}"
        
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
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quality_checks",
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


@dataclass
class Date:
    dt: datetime
    str: "str"
    type: "str"

    @property
    def as_dict(self):
        return {"date": self.str, "type": self.type}


def get_temporal_coverage(resources: list) -> dict:
    """Get maximum temporal coverage of resources

    Case:
    - Table A has data with dates between [X, Y]
    """
    since = Date(datetime.max, None, None)
    until = Date(datetime.min, None, None)
    for resource in resources:
        for cov in resource.coverages.all():
            for dt in cov.datetime_ranges.all():
                if dt.since and dt.since < since.dt:
                    since.dt = dt.since
                    since.str = dt.since_str
                if dt.until and dt.until > until.dt:
                    until.dt = dt.until
                    until.str = dt.until_str
    return {"start": since.str, "end": until.str}


def get_full_temporal_coverage(resources: list) -> dict:
    """Get temporal coverage steps of resources

    Cases:
    - Table A has data with dates between [X, Y], where [X, Y] is open
    - Table A has data with dates between [X, Y], where [X, Y] is closed
    - Table A has data with dates between [X, Y, Z], where [X, Y] is open and [Y, Z] is closed
    """
    open_since = Date(datetime.max, None, "open")
    open_until = Date(datetime.min, None, "open")
    paid_since = Date(datetime.max, None, "closed")
    paid_until = Date(datetime.min, None, "closed")
    for resource in resources:
        for cov in resource.coverages.all():
            for dt in cov.datetime_ranges.all():
                if not cov.is_closed:
                    if dt.since and dt.since < open_since.dt:
                        open_since.dt = dt.since
                        open_since.str = dt.since_str
                    if dt.until and dt.until > open_until.dt:
                        open_until.dt = dt.until
                        open_until.str = dt.until_str
                else:
                    if dt.since and dt.since < paid_since.dt:
                        paid_since.dt = dt.since
                        paid_since.str = dt.since_str
                    if dt.until and dt.until > paid_until.dt:
                        paid_until.dt = dt.until
                        paid_until.str = dt.until_str
    if open_since.str and paid_since.str and paid_until.str:
        paid_since.type = "open"
        return [open_since.as_dict, paid_since.as_dict, paid_until.as_dict]
    if open_since.str and open_until.str and paid_until.str:
        open_until.type = "open"
        return [open_since.as_dict, open_until.as_dict, paid_until.as_dict]
    if open_since.str and open_until.str:
        return [open_since.as_dict, open_until.as_dict]
    if paid_since.str and paid_until.str:
        return [paid_since.as_dict, paid_until.as_dict]

def get_spatial_coverage(resources: list) -> list:
    """Get spatial coverage of resources by returning unique area slugs, keeping only the highest level in each branch
    
    For example:
    - If areas = [br_mg_3100104, br_mg_3100104] -> returns [br_mg_3100104]
    - If areas = [br_mg_3100104, br_sp_3500105] -> returns [br_mg_3100104, br_sp_3500105]
    - If areas = [br_mg, us_ny, us] -> returns [br_mg, us]
    - If areas = [br_mg, world, us] -> returns [world]
    - If resources have no areas -> returns empty list
    """
    # Collect all unique area slugs across resources
    all_areas = set()
    for resource in resources:
        for coverage in resource.coverages.all():
            if coverage.area:
                all_areas.add(coverage.area.slug)
    
    if not all_areas:
        return []
        
    # If 'world' is present, it encompasses everything
    if 'world' in all_areas:
        return ['world']
        
    # Filter out areas that have a parent in the set
    filtered_areas = set()
    for area in all_areas:
        parts = area.split('_')
        is_parent_present = False
        
        # Check if any parent path exists in all_areas
        for i in range(1, len(parts)):
            parent = '_'.join(parts[:i])
            if parent in all_areas:
                is_parent_present = True
                break
                
        if not is_parent_present:
            filtered_areas.add(area)
    
    return sorted(list(filtered_areas))
