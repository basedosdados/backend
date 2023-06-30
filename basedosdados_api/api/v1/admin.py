# -*- coding: utf-8 -*-
import json
from time import sleep

from django.conf import settings
from django.contrib import admin, messages
from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.core.management import call_command
from django.shortcuts import render

# from django.db import models
from django.utils.html import format_html

from google.cloud import bigquery
from google.oauth2 import service_account
from haystack import connections

# from martor.widgets import AdminMartorWidget
from modeltranslation.admin import (
    TabbedTranslationAdmin,
    TranslationStackedInline,
)
from ordered_model.admin import (
    OrderedStackedInline,
    OrderedInlineModelAdminMixin,
)

from basedosdados_api.api.v1.filters import OrganizationImageFilter, TableCoverageFilter
from basedosdados_api.api.v1.forms import (
    ReorderTablesForm,
    ReorderColumnsForm,
)

from basedosdados_api.api.v1.models import (
    Organization,
    Dataset,
    Table,
    InformationRequest,
    RawDataSource,
    BigQueryType,
    Column,
    CloudTable,
    Area,
    Theme,
    Tag,
    Coverage,
    Status,
    Update,
    Availability,
    License,
    Language,
    ObservationLevel,
    Entity,
    EntityCategory,
    Dictionary,
    Pipeline,
    Analysis,
    AnalysisType,
    DateTimeRange,
    Key,
    QualityCheck,
    UUIDHIddenIdForm,
)


def reorder_tables(modeladmin, request, queryset):
    if queryset.count() != 1:
        messages.error(
            request,
            "You can only reorder tables for one dataset at a time",
        )
        return

    if "do_action" in request.POST:
        form = ReorderTablesForm(request.POST)
        if form.is_valid():
            ordered_slugs = form.cleaned_data["ordered_slugs"].split()
            for dataset in queryset:
                call_command("reorder_tables", dataset.id, *ordered_slugs)

            messages.success(request, "Tables reordered successfully")
            return
    else:
        form = ReorderTablesForm()
    return render(
        request,
        "admin/reorder_tables.html",
        {
            "title": "Reorder tables",
            "form": form,
            "datasets": queryset,
        },
    )


reorder_tables.short_description = "Reorder tables"


def reorder_columns(modeladmin, request, queryset):
    if "do_action" in request.POST:
        form = ReorderColumnsForm(request.POST)
        if form.is_valid():
            for table in queryset:
                if form.cleaned_data["use_database_order"]:
                    cloud_table = CloudTable.objects.get(table=table)
                    credentials_dict = json.loads(
                        settings.GOOGLE_APPLICATION_CREDENTIALS
                    )
                    credentials = service_account.Credentials.from_service_account_info(
                        credentials_dict
                    )
                    client = bigquery.Client(credentials=credentials)
                    query = f"""
                        SELECT column_name
                        FROM {cloud_table.gcp_project_id}.{cloud_table.gcp_dataset_id}.INFORMATION_SCHEMA.COLUMNS
                        WHERE table_name = '{cloud_table.gcp_table_id}'
                    """
                    try:
                        query_job = client.query(query, timeout=90)
                    except Exception as e:
                        messages.error(
                            request,
                            f"Error while querying BigQuery: {e}",
                        )
                        return
                    ordered_slugs = [row.column_name for row in query_job.result()]
                else:
                    if queryset.count() != 1:
                        messages.error(
                            request,
                            "To pass the names manually you must select only one table.",
                        )
                        return
                    ordered_slugs = form.cleaned_data["ordered_columns"].split()
                try:
                    call_command("reorder_columns", table.id, *ordered_slugs)
                    print(f"Columns reordered successfully for {table}")
                    sleep(1)
                except Exception as e:
                    messages.error(
                        request,
                        f"Error while reordering columns: {e}",
                    )
                    return
            messages.success(request, "Columns reordered successfully")
            return
    else:
        form = ReorderColumnsForm()

    return render(
        request,
        "admin/reorder_columns.html",
        {"title": "Reorder columns", "tables": queryset, "form": form},
    )


reorder_columns.short_description = "Reorder columns"


def rebuild_search_index(modeladmin, request, queryset):
    call_command("rebuild_index", interactive=False, batchsize=100, workers=4)
    messages.success(request, "Search index rebuilt successfully")


rebuild_search_index.short_description = "Rebuild search index"


def update_search_index(modeladmin, request, queryset):
    for instance in queryset:
        try:
            search_backend = connections["default"].get_backend()
            search_index = search_backend.get_index(
                "basedosdados_api.api.v1.models.Dataset"
            )
            search_index.update_object(instance, using="default")
            messages.success(request, "Search index updated successfully")
        except ObjectDoesNotExist:
            messages.error(request, f"Search index for {instance} update failed")


update_search_index.short_description = "Update search index"


class TranslateOrderedInline(OrderedStackedInline, TranslationStackedInline):
    pass


# Forms


class TableInlineForm(UUIDHIddenIdForm):
    class Meta(UUIDHIddenIdForm):
        model = Table
        fields = [
            "id",
            "slug",
            "name",
            "description",
            "status",
            "license",
            "partner_organization",
            "pipeline",
            "is_directory",
            "published_by",
            "data_cleaned_by",
            "data_cleaning_description",
            "data_cleaning_code_url",
            "raw_data_url",
            "auxiliary_files_url",
            "architecture_url",
            "source_bucket_name",
            "uncompressed_file_size",
            "compressed_file_size",
            "number_rows",
            "number_columns",
            "is_closed",
        ]
        readonly_fields = [
            "order",
            "move_up_down_links",
        ]


class ColumnInlineForm(UUIDHIddenIdForm):
    class Meta(UUIDHIddenIdForm.Meta):
        model = Column
        fields = [
            "id",
            "name",
            "name_staging",
            "description",
            "bigquery_type",
            "is_closed",
            "status",
            "is_primary_key",
            "table",
        ]
        readonly_fields = [
            "order",
            "move_up_down_links",
        ]


class CoverageInlineForm(UUIDHIddenIdForm):
    class Meta(UUIDHIddenIdForm.Meta):
        model = Coverage
        fields = [
            "id",
            "area",
            "table",
        ]


# Inlines


class ColumnInline(TranslateOrderedInline):
    model = Column
    form = ColumnInlineForm
    extra = 0
    show_change_link = True
    show_full_result_count = True
    autocomplete_fields = [
        "directory_primary_key",
        "observation_level",
    ]
    fields = [
        "order",
        "move_up_down_links",
    ] + ColumnInlineForm.Meta.fields
    readonly_fields = [
        "order",
        "move_up_down_links",
    ]
    ordering = [
        "order",
    ]


class TableInline(TranslateOrderedInline):
    model = Table
    form = TableInlineForm
    extra = 0
    show_change_link = True
    fields = [
        "order",
        "move_up_down_links",
    ] + TableInlineForm.Meta.fields
    readonly_fields = [
        "order",
        "move_up_down_links",
    ]
    ordering = [
        "order",
    ]


class RawDataSourceInline(TranslateOrderedInline):
    model = RawDataSource
    extra = 0
    show_change_link = True
    fields = [
        "order",
        "move_up_down_links",
        "id",
        "name",
        "description",
        "url",
    ]
    readonly_fields = [
        "order",
        "move_up_down_links",
    ]
    ordering = [
        "order",
    ]


class InformationRequestInline(TranslateOrderedInline):
    model = InformationRequest
    extra = 0
    show_change_link = True
    fields = [
        "order",
        "move_up_down_links",
        "id",
        "origin",
        "number",
        "url",
    ]
    readonly_fields = [
        "order",
        "move_up_down_links",
    ]
    ordering = [
        "order",
    ]


class DateTimeRangeInline(admin.StackedInline):
    model = DateTimeRange
    extra = 0
    show_change_link = True


class CoverageTableInline(admin.StackedInline):
    model = Coverage
    form = CoverageInlineForm
    extra = 0
    show_change_link = True
    exclude = [
        "raw_data_source",
        "information_request",
        "column",
        "key",
        "analysis",
    ]
    readonly_fields = [
        "id",
        "area",
        # "table",
    ]
    inlines = [
        DateTimeRangeInline,
    ]
    # template = "admin/edit_inline/custom_coverage_model_inline.html"
    # inlines = [
    #     TableCoverageFilter,
    # ]
    # formfield_overrides = {models.TextField: {"widget": AdminMartorWidget}}


# Model Admins
class AreaAdmin(TabbedTranslationAdmin):
    readonly_fields = [
        "id",
    ]
    list_display = [
        "name",
        "slug",
    ]
    search_fields = [
        "name",
        "slug",
    ]


class OrganizationAdmin(TabbedTranslationAdmin):
    readonly_fields = ["id", "full_slug", "created_at", "updated_at"]
    list_display = ["name", "full_slug", "has_picture"]
    search_fields = ["name", "slug"]
    list_filter = [OrganizationImageFilter, "created_at", "updated_at"]
    autocomplete_fields = [
        "area",
    ]


class ThemeAdmin(TabbedTranslationAdmin):
    readonly_fields = ["id", "created_at", "updated_at"]
    list_display = [
        "name",
        "slug",
    ]
    search_fields = [
        "name",
        "slug",
    ]


class TagAdmin(TabbedTranslationAdmin):
    readonly_fields = ["id", "created_at", "updated_at"]
    list_display = [
        "name",
        "slug",
    ]
    search_fields = [
        "name",
        "slug",
    ]


class DatasetAdmin(OrderedInlineModelAdminMixin, TabbedTranslationAdmin):
    actions = [
        reorder_tables,
        rebuild_search_index,
    ]

    def related_objects(self, obj):
        return format_html(
            "<a class='related-widget-wrapper-link add-related' href='/admin/v1/table/add/?dataset={0}&_to_field=id&_popup=1'>{1} {2}</a>",  # noqa
            obj.id,
            obj.tables.count(),
            " ".join(
                ["tables" if obj.tables.count() > 1 else "table", "(click to add)"]
            ),
        )

    related_objects.short_description = "Tables"

    # formfield_overrides = {models.TextField: {"widget": AdminMartorWidget}}
    readonly_fields = [
        "id",
        "full_slug",
        "coverage",
        "contains_tables",
        "contains_open_tables",
        "contains_closed_tables",
        "contains_raw_data_sources",
        "contains_information_requests",
        "created_at",
        "updated_at",
        "related_objects",
    ]
    list_display = ["name", "full_slug", "coverage", "organization", "related_objects"]
    search_fields = ["name", "slug", "organization__name"]
    inlines = [
        TableInline,
        RawDataSourceInline,
        InformationRequestInline,
    ]
    filter_horizontal = [
        "tags",
        "themes",
    ]
    list_filter = [
        "organization__name",
    ]


class TableAdmin(OrderedInlineModelAdminMixin, TabbedTranslationAdmin):
    actions = [
        reorder_columns,
    ]

    change_form_template = "admin/table_change_form.html"

    def related_columns(self, obj):
        return format_html(
            "<a href='/admin/v1/column/add/?table={0}'>{1} {2}</a>",
            obj.id,
            obj.columns.count(),
            " ".join(
                ["columns" if obj.columns.count() > 1 else "column", "(click to add)"]
            ),
        )

    related_columns.short_description = "Columns"

    def related_coverages(self, obj):
        qs = DateTimeRange.objects.filter(coverage=obj)
        lines = []
        for datetimerange in qs:
            lines.append(
                '<a href="/admin/api/v1/datetimerange/{0}/change/" target="_blank">Date Time Range</a>',
                datetimerange.pk,
            )
        return format_html(
            '<a href="/admin/api/v1/datetimerange/{}/change/" target="_blank">Date Time Range</a>',
            # 'http://localhost:8001/admin/v1/datetimerange/00004e41-a4f8-48eb-b39c-f353d872d7c7/change/'
            obj.datetimerange.slug,
        )

    related_coverages.short_description = "Coverages"

    def add_view(self, request, *args, **kwargs):
        parent_model_id = request.GET.get("dataset")
        if parent_model_id:
            # If a parent model ID is provided, add the parent model field to the form
            # fields = self.get_related_fields
            initial = {"parent_model": parent_model_id}
            self.initial = initial  # noqa
        return super().add_view(request, *args, **kwargs)

    def get_related_fields(self, request, obj=None):  # noqa
        fields = self.model._meta.fields  # noqa
        parent_model_id = request.GET.get("dataset")
        if parent_model_id:
            parent_model = Dataset.objects.get(id=parent_model_id)
            fields += parent_model._meta.fields  # noqa
        return fields

    readonly_fields = [
        "id",
        "partitions",
        "created_at",
        "updated_at",
        "related_columns",
    ]
    search_fields = ["name", "dataset__name"]
    inlines = [
        ColumnInline,
    ]
    autocomplete_fields = [
        "dataset",
        "partner_organization",
        "published_by",
        "data_cleaned_by",
    ]
    list_filter = [
        "dataset__organization__name",
        TableCoverageFilter,
    ]


class ColumnForm(forms.ModelForm):
    class Meta:
        model = Column
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["directory_primary_key"].queryset = Column.objects.filter(
            table__is_directory=True
        )


class ColumnAdmin(TabbedTranslationAdmin):
    form = ColumnForm
    readonly_fields = [
        "id",
        "order",
    ]
    list_display = [
        "__str__",
        "table",
    ]
    search_fields = ["name", "table__name"]
    autocomplete_fields = [
        "table",
        "observation_level",
    ]
    list_filter = [
        "table__dataset__organization__name",
    ]
    # formfield_overrides = {models.TextField: {"widget": AdminMartorWidget}}


class ObservationLevelAdmin(admin.ModelAdmin):
    readonly_fields = [
        "id",
    ]
    search_fields = ["name", "entity__name"]
    autocomplete_fields = [
        "entity",
        "table",
        "raw_data_source",
        "information_request",
    ]
    list_filter = [
        "entity__category__name",
    ]
    list_display = [
        "__str__",
        "table",
        "raw_data_source",
        "information_request",
    ]
    inlines = [
        ColumnInline,
    ]


class RawDataSourceAdmin(TabbedTranslationAdmin):
    readonly_fields = ["id", "created_at", "updated_at"]
    list_display = ["name", "dataset", "created_at", "updated_at"]
    search_fields = ["name", "dataset__name"]
    autocomplete_fields = [
        "dataset",
        "languages",
    ]
    filter_horizontal = [
        "languages",
        "area_ip_address_required",
    ]
    # formfield_overrides = {models.TextField: {"widget": AdminMartorWidget}}


class InformationRequestAdmin(TabbedTranslationAdmin):
    readonly_fields = ["id", "created_at", "updated_at"]
    list_display = ["__str__", "dataset", "created_at", "updated_at"]
    search_fields = ["__str__", "dataset__name"]
    autocomplete_fields = [
        "dataset",
    ]
    # formfield_overrides = {models.TextField: {"widget": AdminMartorWidget}}


class CoverageTypeAdminFilter(admin.SimpleListFilter):
    title = "coverage_type"
    parameter_name = "coverage_type"

    def lookups(self, request, model_admin):
        return (
            ("table", "Table"),
            ("column", "Column"),
            ("raw_data_source", "Raw Data Source"),
            ("information_request", "Information Request"),
            ("key", "Key"),
        )

    def queryset(self, request, queryset):
        if self.value() == "table":
            return queryset.filter(table__isnull=False)
        if self.value() == "column":
            return queryset.filter(column__isnull=False)
        if self.value() == "raw_data_source":
            return queryset.filter(raw_data_source__isnull=False)
        if self.value() == "information_request":
            return queryset.filter(information_request__isnull=False)
        if self.value() == "key":
            return queryset.filter(key__isnull=False)


class DateTimeRangeInline(admin.StackedInline):
    model = DateTimeRange
    extra = 0
    show_change_link = True


class DateTimeRangeAdmin(admin.ModelAdmin):
    readonly_fields = ["id"]
    list_display = ["__str__", "coverage"]
    autocomplete_fields = [
        "coverage",
    ]


class CoverageAdmin(admin.ModelAdmin):
    readonly_fields = ["id"]
    list_display = ["area", "coverage_type", "table"]
    list_filter = [
        CoverageTypeAdminFilter,
    ]
    autocomplete_fields = [
        "table",
        "raw_data_source",
        "information_request",
        "column",
    ]
    search_fields = [
        "table__name",
        "raw_data_source__name",
        "information_request__dataset__name",
        "column__name",
    ]
    inlines = [
        DateTimeRangeInline,
    ]


class EntityCategoryAdmin(TabbedTranslationAdmin):
    readonly_fields = [
        "id",
    ]
    list_display = [
        "name",
        "slug",
    ]
    search_fields = [
        "name",
        "slug",
    ]


class EntityAdmin(TabbedTranslationAdmin):
    readonly_fields = [
        "id",
    ]
    list_display = [
        "name",
        "category",
    ]
    search_fields = ["name", "category__name"]
    list_filter = [
        "category",
    ]
    autocomplete_fields = [
        "category",
    ]


class LanguageAdmin(TabbedTranslationAdmin):
    readonly_fields = [
        "id",
    ]
    list_display = [
        "name",
        "slug",
    ]
    search_fields = [
        "name",
        "slug",
    ]


class UpdateAdmin(admin.ModelAdmin):
    readonly_fields = [
        "id",
    ]
    list_display = [
        "__str__",
    ]
    search_fields = [
        "entity",
        "table",
        "raw_data_source",
        "information_request",
        "column",
    ]
    autocomplete_fields = [
        "entity",
        "table",
        "raw_data_source",
        "information_request",
    ]


class LicenseAdmin(TabbedTranslationAdmin):
    readonly_fields = [
        "id",
    ]
    list_display = [
        "name",
        "slug",
    ]
    search_fields = [
        "name",
        "slug",
    ]


class AvailabilityAdmin(TabbedTranslationAdmin):
    readonly_fields = [
        "id",
    ]
    list_display = [
        "name",
        "slug",
    ]
    search_fields = [
        "name",
        "slug",
    ]


class CloudTableAdmin(admin.ModelAdmin):
    readonly_fields = [
        "id",
    ]
    list_display = [
        "__str__",
    ]
    search_fields = [
        "gcp_project_id",
        "gcp_dataset_id",
        "gcp_table_id",
    ]
    autocomplete_fields = ["table", "columns"]
    filter_horizontal = [
        "columns",
    ]


class StatusAdmin(TabbedTranslationAdmin):
    readonly_fields = [
        "id",
    ]
    list_display = [
        "name",
        "slug",
    ]
    search_fields = [
        "name",
        "slug",
    ]


class AnalysisTypeAdmin(TabbedTranslationAdmin):
    readonly_fields = [
        "id",
    ]
    list_display = [
        "name",
        "slug",
    ]
    search_fields = [
        "name",
        "slug",
    ]


class AnalysisAdmin(TabbedTranslationAdmin):
    readonly_fields = [
        "id",
    ]
    list_display = [
        "name",
        "analysis_type",
    ]
    search_fields = [
        "name",
        "description",
    ]
    autocomplete_fields = ["analysis_type", "datasets", "themes", "tags"]
    filter_horizontal = ["datasets", "themes", "tags"]


class KeyAdmin(admin.ModelAdmin):
    readonly_fields = [
        "id",
    ]
    list_display = [
        "name",
        "value",
    ]
    search_fields = [
        "name",
        "value",
    ]


class QualityCheckAdmin(TabbedTranslationAdmin):
    readonly_fields = [
        "id",
    ]
    list_display = [
        "name",
        "analysis",
        "dataset",
        "passed",
    ]
    search_fields = [
        "name",
        "description",
    ]
    autocomplete_fields = [
        "analysis",
        "dataset",
        "table",
        "column",
        "key",
        "raw_data_source",
        "information_request",
    ]


admin.site.register(Analysis, AnalysisAdmin)
admin.site.register(AnalysisType, AnalysisTypeAdmin)
admin.site.register(Area, AreaAdmin)
admin.site.register(Availability, AvailabilityAdmin)
admin.site.register(BigQueryType)
admin.site.register(CloudTable, CloudTableAdmin)
admin.site.register(Column, ColumnAdmin)
admin.site.register(Coverage, CoverageAdmin)
admin.site.register(Dataset, DatasetAdmin)
admin.site.register(DateTimeRange, DateTimeRangeAdmin)
admin.site.register(Dictionary)
admin.site.register(Entity, EntityAdmin)
admin.site.register(EntityCategory, EntityCategoryAdmin)
admin.site.register(InformationRequest, InformationRequestAdmin)
admin.site.register(Key, KeyAdmin)
admin.site.register(Language, LanguageAdmin)
admin.site.register(License, LicenseAdmin)
admin.site.register(ObservationLevel, ObservationLevelAdmin)
admin.site.register(Organization, OrganizationAdmin)
admin.site.register(Pipeline)
admin.site.register(RawDataSource, RawDataSourceAdmin)
admin.site.register(Status, StatusAdmin)
admin.site.register(Table, TableAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Theme, ThemeAdmin)
admin.site.register(Update, UpdateAdmin)
admin.site.register(QualityCheck, QualityCheckAdmin)
