# -*- coding: utf-8 -*-
from time import sleep

from django import forms
from django.contrib import admin, messages
from django.contrib.admin import ModelAdmin
from django.core.management import call_command
from django.db.models.query import QuerySet
from django.http import HttpRequest
from django.shortcuts import render
from django.utils.html import format_html
from modeltranslation.admin import TabbedTranslationAdmin, TranslationStackedInline
from ordered_model.admin import OrderedInlineModelAdminMixin, OrderedStackedInline

from bd_api.apps.api.v1.filters import (
    DatasetOrganizationListFilter,
    OrganizationImageListFilter,
    TableCoverageListFilter,
    TableDirectoryListFilter,
    TableObservationListFilter,
    TableOrganizationListFilter,
)
from bd_api.apps.api.v1.forms import (
    CloudTableInlineForm,
    ColumnInlineForm,
    ColumnOriginalNameInlineForm,
    CoverageInlineForm,
    ObservationLevelInlineForm,
    ReorderColumnsForm,
    ReorderTablesForm,
    TableInlineForm,
    UpdateInlineForm,
)
from bd_api.apps.api.v1.models import (
    Analysis,
    AnalysisType,
    Area,
    Availability,
    BigQueryType,
    CloudTable,
    Column,
    ColumnOriginalName,
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
    TableNeighbor,
    Tag,
    Theme,
    Update,
)
from bd_api.apps.api.v1.tasks import (
    rebuild_search_index_task,
    update_page_views_task,
    update_search_index_task,
    update_table_metadata_task,
    update_table_neighbors_task,
)
from bd_api.custom.client import get_gbq_client

################################################################################
# Model Admins Inlines
################################################################################


class OrderedTranslatedInline(OrderedStackedInline, TranslationStackedInline):
    pass


class ColumnInline(OrderedTranslatedInline):
    model = Column
    form = ColumnInlineForm
    extra = 0
    show_change_link = True
    show_full_result_count = True
    fields = ColumnInlineForm.Meta.fields + [
        "order",
        "move_up_down_links",
    ]
    readonly_fields = [
        "order",
        "move_up_down_links",
    ]
    autocomplete_fields = [
        "directory_primary_key",
    ]
    ordering = [
        "order",
    ]

    def get_formset(self, request, obj=None, **kwargs):
        """Get formset, and save the current object"""
        self.current_obj = obj
        return super().get_formset(request, obj, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Limit the observation level queryset to the current object"""
        if db_field.name == "observation_level":
            kwargs["queryset"] = ObservationLevel.objects.filter(table=self.current_obj)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ColumnOriginalNameInline(TranslationStackedInline):
    model = ColumnOriginalName
    form = ColumnOriginalNameInlineForm
    extra = 0
    fields = [
        "id",
        "name",
    ]


class CloudTableInline(admin.StackedInline):
    model = CloudTable
    form = CloudTableInlineForm
    extra = 0
    fields = [
        "id",
        "gcp_project_id",
        "gcp_dataset_id",
        "gcp_table_id",
    ]


class ObservationLevelInline(admin.StackedInline):
    model = ObservationLevel
    form = ObservationLevelInlineForm
    extra = 0
    fields = [
        "id",
        "entity",
    ]
    autocomplete_fields = [
        "entity",
    ]


class TableInline(OrderedTranslatedInline):
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


class RawDataSourceInline(OrderedTranslatedInline):
    model = RawDataSource
    extra = 0
    show_change_link = True
    fields = [
        "order",
        "move_up_down_links",
        "id",
        "name",
        "description",
        "availability",
        "url",
    ]
    readonly_fields = [
        "order",
        "move_up_down_links",
    ]
    ordering = [
        "order",
    ]


class InformationRequestInline(OrderedTranslatedInline):
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


class CoverageInline(admin.StackedInline):
    model = Coverage
    form = CoverageInlineForm
    extra = 0
    show_change_link = True
    readonly_fields = ["datetime_ranges"]

    def datetime_ranges(self, cov):
        """Show datetime ranges in coverage inline"""
        return [str(dt) for dt in cov.datetime_ranges.all()]


class UpdateInline(admin.StackedInline):
    model = Update
    form = UpdateInlineForm
    extra = 0
    fields = [
        "id",
        "entity",
        "lag",
        "latest",
        "frequency",
    ]
    autocomplete_fields = [
        "entity",
    ]


################################################################################
# Model Admins Actions
################################################################################


def update_search_index(modeladmin, request, queryset):
    update_search_index_task()


update_search_index.short_description = "Atualizar index de busca"


def rebuild_search_index(modeladmin, request, queryset):
    rebuild_search_index_task()


rebuild_search_index.short_description = "Reconstruir index de busca"


def update_table_metadata(modeladmin: ModelAdmin, request: HttpRequest, queryset: QuerySet):
    """Update the metadata of selected tables in the admin"""
    if str(modeladmin) == "v1.TableAdmin":
        tables = queryset.all()
    if str(modeladmin) == "v1.DatasetAdmin":
        tables = Table.objects.filter(dataset__in=queryset).all()

    update_table_metadata_task([t.pk for t in tables])


update_table_metadata.short_description = "Atualizar metadados das tabelas"


def update_table_neighbors(modeladmin: ModelAdmin, request: HttpRequest, queryset: QuerySet):
    """Update all table neighbors"""
    update_table_neighbors_task()


update_table_neighbors.short_description = "Atualizar os vizinhos das tabelas"


def update_page_views(modeladmin: ModelAdmin, request: HttpRequest, queryset: QuerySet):
    """Update the page views counter of all datasets and tables"""
    update_page_views_task()


update_page_views.short_description = "Atualizar metadados de visualizações"


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
                    cloud_table_slug = f"{cloud_table.gcp_project_id}.{cloud_table.gcp_dataset_id}"
                    query = f"""
                        SELECT column_name
                        FROM {cloud_table_slug}.INFORMATION_SCHEMA.COLUMNS
                        WHERE table_name = '{cloud_table.gcp_table_id}'
                    """
                    try:
                        client = get_gbq_client()
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

    tables = queryset.first()
    tables = tables.columns.order_by("name").all()
    for i, table in enumerate(tables):
        table.order = i
        table.save()


reset_column_order.short_description = "Reiniciar ordem das colunas"


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
    list_filter = [OrganizationImageListFilter, "created_at", "updated_at"]
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
        update_page_views,
        update_search_index,
        rebuild_search_index,
    ]
    inlines = [
        TableInline,
        RawDataSourceInline,
        InformationRequestInline,
    ]
    readonly_fields = [
        "id",
        "full_slug",
        "coverage",
        "contains_tables",
        "contains_raw_data_sources",
        "contains_information_requests",
        "created_at",
        "updated_at",
        "related_objects",
    ]
    search_fields = ["name", "slug", "organization__name"]
    filter_horizontal = [
        "tags",
        "themes",
    ]
    list_filter = [
        DatasetOrganizationListFilter,
    ]
    list_display = [
        "name",
        "organization",
        "coverage",
        "related_objects",
        "page_views",
        "created_at",
        "updated_at",
    ]
    ordering = ["-updated_at"]

    def related_objects(self, obj):
        return format_html(
            "<a class='related-widget-wrapper-link add-related' "
            "href='/admin/v1/table/add/?dataset={0}&_to_field=id&_popup=1'>{1} {2}</a>",
            obj.id,
            obj.tables.count(),
            "tables" if obj.tables.count() > 1 else "table",
        )

    related_objects.short_description = "Tables"


class TableAdmin(OrderedInlineModelAdminMixin, TabbedTranslationAdmin):
    actions = [
        reorder_columns,
        reset_column_order,
        update_table_metadata,
        update_table_neighbors,
        update_page_views,
    ]
    inlines = [
        ColumnInline,
        CoverageInline,
        CloudTableInline,
        ObservationLevelInline,
        UpdateInline,
    ]
    readonly_fields = [
        "id",
        "partitions",
        "created_at",
        "updated_at",
    ]
    search_fields = [
        "name",
        "dataset__name",
    ]
    autocomplete_fields = [
        "dataset",
        "partner_organization",
        "published_by",
        "data_cleaned_by",
    ]
    list_display = [
        "name",
        "dataset",
        "number_columns",
        "number_rows",
        "uncompressed_file_size",
        "page_views",
        "created_at",
        "updated_at",
    ]
    list_filter = [
        TableOrganizationListFilter,
        TableCoverageListFilter,
        TableObservationListFilter,
        TableDirectoryListFilter,
    ]
    ordering = ["-updated_at"]

    def get_form(self, request, obj=None, **kwargs):
        """Get form, and save the current object"""
        self.current_obj = obj
        return super().get_form(request, obj, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "raw_data_source":
            kwargs["queryset"] = RawDataSource.objects.filter(dataset=self.current_obj.dataset)
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class TableNeighborAdmin(admin.ModelAdmin):
    search_fields = [
        "table_a__name",
        "table_b__name",
    ]
    list_filter = [
        "table_a",
        "table_b",
    ]
    list_display = [
        "table_a",
        "table_b",
        "similarity",
        "similarity_of_area",
        "similarity_of_datetime",
        "similarity_of_directory",
    ]
    ordering = ["table_a", "table_b"]


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
    list_display = [
        "__str__",
        "table",
    ]
    list_filter = [
        "table__dataset__organization__name",
    ]
    autocomplete_fields = [
        "table",
        "observation_level",
    ]
    readonly_fields = [
        "id",
        "order",
    ]
    search_fields = ["name", "table__name"]
    inlines = [
        CoverageInline,
        ColumnOriginalNameInline,
    ]


class ColumnOriginalNameAdmin(TabbedTranslationAdmin):
    readonly_fields = [
        "id",
    ]
    list_display = [
        "__str__",
    ]
    fields = [
        "id",
        "name",
        "column",
    ]
    inlines = [CoverageInline]


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
    list_display = ["name", "dataset", "created_at", "updated_at"]
    search_fields = ["name", "dataset__name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    autocomplete_fields = [
        "dataset",
        "languages",
    ]
    filter_horizontal = [
        "languages",
        "area_ip_address_required",
    ]
    inlines = [CoverageInline]


class InformationRequestAdmin(TabbedTranslationAdmin):
    list_display = ["__str__", "dataset", "created_at", "updated_at"]
    search_fields = ["__str__", "dataset__name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    autocomplete_fields = ["dataset"]
    inlines = [CoverageInline, ObservationLevelInline]


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


class DateTimeRangeAdmin(admin.ModelAdmin):
    list_display = ["__str__", "coverage"]
    readonly_fields = ["id"]
    autocomplete_fields = [
        "coverage",
    ]
    exclude = [
        "start_quarter",
        "start_semester",
        "start_hour",
        "start_minute",
        "start_second",
        "end_quarter",
        "end_semester",
        "end_hour",
        "end_minute",
        "end_second",
    ]


class CoverageAdmin(admin.ModelAdmin):
    readonly_fields = ["id"]
    list_display = [
        "area",
        "coverage_type",
        "table",
        "column",
        "raw_data_source",
        "information_request",
    ]
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
    inlines = [CoverageInline]


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
admin.site.register(ColumnOriginalName, ColumnOriginalNameAdmin)
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
admin.site.register(TableNeighbor, TableNeighborAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Theme, ThemeAdmin)
admin.site.register(Update, UpdateAdmin)
admin.site.register(QualityCheck, QualityCheckAdmin)
