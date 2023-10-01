# -*- coding: utf-8 -*-
import json
from time import sleep

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.core.management import call_command
from django.db.models.query import QuerySet
from django.forms.models import BaseInlineFormSet
from django.shortcuts import get_object_or_404, render
from django.utils.html import format_html
from google.api_core.exceptions import BadRequest, NotFound
from google.cloud.bigquery import Client
from google.oauth2 import service_account
from loguru import logger
from modeltranslation.admin import TabbedTranslationAdmin, TranslationStackedInline
from ordered_model.admin import OrderedInlineModelAdminMixin, OrderedStackedInline
from pandas import read_gbq

from basedosdados_api.api.v1.filters import (
    OrganizationImageFilter,
    TableCoverageFilter,
    TableObservationFilter,
)
from basedosdados_api.api.v1.forms import (
    ColumnInlineForm,
    CoverageInlineForm,
    ObservationLevelForm,
    ReorderColumnsForm,
    ReorderTablesForm,
    TableInlineForm,
)
from basedosdados_api.api.v1.models import (
    Analysis,
    AnalysisType,
    Area,
    Availability,
    BigQueryType,
    CloudTable,
    Column,
    Coverage,
    Dataset,
    DateTimeRange,
    Dictionary,
    Entity,
    EntityCategory,
    InformationRequest,
    Key,
    Language,
    License,
    ObservationLevel,
    Organization,
    Pipeline,
    QualityCheck,
    RawDataSource,
    Status,
    Table,
    Tag,
    Theme,
    Update,
)

################################################################################
# Model Admins Inlines
################################################################################


class TranslateOrderedInline(OrderedStackedInline, TranslationStackedInline):
    pass


class CustomObservationLevelInlineFormset(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        columns_queryset = self.instance.columns.all()

        for form in self.forms:
            form.fields["column_choice"].queryset = columns_queryset


class ObservationLevelInline(admin.StackedInline):
    model = ObservationLevel
    form = ObservationLevelForm
    formset = CustomObservationLevelInlineFormset
    template = "admin/edit_inline/stacked_table_observation_level.html"
    extra = 0

    fields = [
        "id",
        "entity",
        "column_choice",
    ]
    autocomplete_fields = [
        "entity",
    ]


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


################################################################################
# Model Admins Actions
################################################################################


def get_credentials():
    """Get google cloud credentials"""
    credentials_dict = json.loads(settings.GOOGLE_APPLICATION_CREDENTIALS)
    credentials = service_account.Credentials.from_service_account_info(credentials_dict)
    return credentials


def update_table_metadata(modeladmin=None, request=None, queryset: QuerySet = None):
    """Update the metadata of selected tables in the database"""

    creds = get_credentials()
    client = Client(credentials=creds)

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
            bq_table = client.get_table(table.db_slug)
            table.number_rows = bq_table.num_rows or None
            table.number_columns = len(bq_table.schema) or None
            table.uncompressed_file_size = bq_table.num_bytes or None
            if bq_table.table_type == "VIEW":
                table.number_rows = read_gbq(
                    """
                    SELECT COUNT(1) AS n_rows
                    FROM `{table.db_slug}`
                """
                ).loc[0, "n_rows"]
            table.save()
        except (BadRequest, NotFound, ValueError) as e:
            logger.warning(e)


update_table_metadata.short_description = "Atualizar metadados das tabelas"


def reorder_tables(modeladmin, request, queryset):
    """Reorder tables in respect to dataset"""

    if queryset.count() != 1:
        message = "Você só pode selecionar um conjunto de dados por vez"
        messages.error(request, message)
        return

    if "do_action" in request.POST:
        form = ReorderTablesForm(request.POST)
        if form.is_valid():
            ordered_slugs = form.cleaned_data["ordered_slugs"].split()
            for dataset in queryset:
                call_command("reorder_tables", dataset.id, *ordered_slugs)
            messages.success(request, "Tabelas reordenadas com sucesso")
    else:
        form = ReorderTablesForm()
        dataset = queryset.first()
        tables = dataset.tables.all()
        return render(
            request,
            "admin/reorder_tables.html",
            {
                "title": "Editar ordem das tabelas",
                "form": form,
                "tables": tables,
                "dataset": dataset,
            },
        )


reorder_tables.short_description = "Editar ordem das tabelas"


def reset_table_order(modeladmin, request, queryset):
    """Reset table order in respect to dataset"""

    if queryset.count() != 1:
        message = "Você só pode selecionar um conjunto de dados por vez"
        messages.error(request, message)
        return

    dataset = queryset.first()
    for i, table in enumerate(dataset.tables.order_by("name").all()):
        table.order = i
        table.save()


reset_table_order.short_description = "Reiniciar ordem das tabelas"


def reorder_columns(modeladmin, request, queryset):
    """Reorder columns in respect to table"""

    if "do_action" in request.POST:
        form = ReorderColumnsForm(request.POST)
        if form.is_valid():
            for table in queryset:
                if form.cleaned_data["use_database_order"]:
                    cloud_table = CloudTable.objects.get(table=table)
                    query = f"""
                        SELECT column_name
                        FROM {cloud_table.gcp_project_id}.{cloud_table.gcp_dataset_id}.INFORMATION_SCHEMA.COLUMNS
                        WHERE table_name = '{cloud_table.gcp_table_id}'
                    """
                    try:
                        creds = get_credentials()
                        client = Client(credentials=creds)
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
    else:
        form = ReorderColumnsForm()
        return render(
            request,
            "admin/reorder_columns.html",
            {"title": "Reorder columns", "tables": queryset, "form": form},
        )


reorder_columns.short_description = "Alterar ordem das colunas"


def reset_column_order(modeladmin, request, queryset):
    """Reset column order in respect to dataset"""

    if queryset.count() != 1:
        message = "Você só pode selecionar um conjunto de dados por vez"
        messages.error(request, message)
        return

    table = queryset.first()
    for i, table in enumerate(table.columns.order_by("name").all()):
        table.order = i
        table.save()


reset_column_order.short_description = "Reiniciar ordem das colunas"


def update_search_index(modeladmin, request, queryset):
    """Update the search index"""
    call_command("update_index", batchsize=100, workers=4)
    messages.success(request, "Search index updated successfully")


update_search_index.short_description = "Atualizar index de busca"


def reset_search_index(modeladmin, request, queryset):
    """Reset the search index"""
    call_command("rebuild_index", interactive=False, batchsize=100, workers=4)
    messages.success(request, "Search index rebuilt successfully")


reset_search_index.short_description = "Reiniciar index de busca"


################################################################################
# Model Admins
################################################################################


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
        reset_table_order,
        update_table_metadata,
        update_search_index,
        reset_search_index,
    ]

    def related_objects(self, obj):
        return format_html(
            "<a class='related-widget-wrapper-link add-related' href='/admin/v1/table/add/?dataset={0}&_to_field=id&_popup=1'>{1} {2}</a>",  # noqa  pylint: disable=line-too-long
            obj.id,
            obj.tables.count(),
            " ".join(["tables" if obj.tables.count() > 1 else "table", "(click to add)"]),
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
        reset_column_order,
        update_table_metadata,
    ]

    change_form_template = "admin/table_change_form.html"

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        """Adds custom context to the change form view"""
        extra_context = extra_context or {}
        obj = get_object_or_404(Table, pk=object_id) if object_id else None
        if obj:
            coverages = obj.coverages.all()
            coverages_list = []
            for coverage in coverages:
                cov = {
                    "id": coverage.id,
                    "area": coverage.area.name,
                    "datetime_range": "",
                }
                datetime_range = (
                    coverage.datetime_ranges.first()
                )  # currently, it gets only the first datetime_range
                if datetime_range:
                    cov["datetime_range"] = datetime_range
                coverages_list.append(cov)

            extra_context["table_coverages"] = coverages_list

            extra_context["datetime_ranges"] = [
                coverage.datetime_ranges.all() for coverage in obj.coverages.all()
            ]

            observations = obj.observation_levels.all()
            observations_list = []
            for observation in observations:
                obs = {
                    "id": observation.id,
                    "entity": observation.entity.name,
                    "columns": "",
                }
                columns = [column.name for column in observation.columns.all()]
                if columns:
                    obs["columns"] = ",".join(columns)
                observations_list.append(obs)

            extra_context["table_observations"] = observations_list

            cloudtables = obj.cloud_tables.all()
            cloudtables_list = []
            for cloudtable in cloudtables:
                ct = {
                    "id": cloudtable.id,
                    "gcp_project_id": cloudtable.gcp_project_id,
                    "gcp_dataset_id": cloudtable.gcp_dataset_id,
                    "gcp_table_id": cloudtable.gcp_table_id,
                    "columns": "",
                }
                cloudtables_list.append(ct)

            extra_context["table_cloudtables"] = cloudtables_list

        return super().changeform_view(request, object_id, form_url, extra_context=extra_context)

    def related_columns(self, obj):
        """Adds information of number of columns, with link to add a new column"""
        return format_html(
            "<a href='/admin/v1/column/add/?table={0}'>{1} {2}</a>",
            obj.id,
            obj.columns.count(),
            " ".join(["columns" if obj.columns.count() > 1 else "column", "(click to add)"]),
        )

    related_columns.short_description = "Columns"

    def related_coverages(self, obj):
        qs = DateTimeRange.objects.filter(coverage=obj)
        lines = []
        for datetimerange in qs:
            lines.append(
                '<a href="/admin/api/v1/datetimerange/{0}/change/" target="_blank">Date Time Range</a>',  # noqa  pylint: disable=line-too-long
                datetimerange.pk,
            )
        return format_html(
            '<a href="/admin/api/v1/datetimerange/{}/change/" target="_blank">Date Time Range</a>',  # noqa  pylint: disable=line-too-long
            obj.datetimerange.slug,
        )

    related_coverages.short_description = "Coverages"

    def add_view(self, request, *args, **kwargs):
        parent_model_id = request.GET.get("dataset")
        if parent_model_id:
            # If a parent model ID is provided, add the parent model field to the form
            initial = {"parent_model": parent_model_id}
            self.initial = initial  # noqa
        return super().add_view(request, *args, **kwargs)

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
        ObservationLevelInline,
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
        TableObservationFilter,
    ]

    def save_formset(self, request, form, formset, change):
        """Saves the formset, adding the table to the dataset"""
        if formset.model == ObservationLevel:
            instances = formset.save(commit=False)  # noqa
            for form in formset.forms:
                if form.instance.pk:
                    Column.objects.filter(observation_level=form.instance).update(
                        observation_level=None
                    )
                form_instance = form.save(commit=False)
                column_instance = form.cleaned_data.get("column_choice")
                if column_instance:
                    column_instance.observation_level = form_instance
                    column_instance.save()
                form_instance.save()
            formset.save_m2m()
        else:
            formset.save()


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
    search_fields = [
        "table__name",
        "entity__name",
        "raw_data_source__name",
        "information_request__dataset__name",
    ]
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
    fields = [
        "table",
        "gcp_project_id",
        "gcp_dataset_id",
        "gcp_table_id",
        "columns",
    ]
    readonly_fields = [
        "id",
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
