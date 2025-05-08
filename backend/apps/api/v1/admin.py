# -*- coding: utf-8 -*-
from time import sleep

from django import forms
from django.contrib import admin, messages
from django.contrib.admin import ModelAdmin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.core.management import call_command
from django.db.models.query import QuerySet
from django.http import HttpRequest
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from modeltranslation.admin import TabbedTranslationAdmin, TranslationStackedInline
from ordered_model.admin import OrderedInlineModelAdminMixin, OrderedStackedInline

from backend.apps.api.v1.filters import (
    AreaAdministrativeLevelFilter,
    AreaParentFilter,
    OrganizationImageListFilter,
    TableCoverageListFilter,
    TableDirectoryListFilter,
    TableObservationListFilter,
    TableOrganizationListFilter,
)
from backend.apps.api.v1.forms import (
    ColumnInlineForm,
    ColumnOriginalNameInlineForm,
    CoverageInlineForm,
    MeasurementUnitInlineForm,
    ObservationLevelInlineForm,
    PollInlineForm,
    ReorderColumnsForm,
    ReorderObservationLevelsForm,
    ReorderTablesForm,
    TableForm,
    TableInlineForm,
    UpdateInlineForm,
)
from backend.apps.api.v1.models import (
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
    MeasurementUnit,
    MeasurementUnitCategory,
    ObservationLevel,
    Organization,
    Pipeline,
    Poll,
    QualityCheck,
    RawDataSource,
    Status,
    Table,
    TableNeighbor,
    Tag,
    Theme,
    Update,
)
from backend.apps.api.v1.tasks import (
    rebuild_search_index_task,
    update_page_views_task,
    update_search_index_task,
    update_table_metadata_task,
    update_table_neighbors_task,
)
from backend.custom.client import get_gbq_client

################################################################################
# Model Admins Inlines
################################################################################


class OrderedTranslatedInline(OrderedStackedInline, TranslationStackedInline):
    pass


class MeasurementUnitInline(OrderedTranslatedInline):
    model = MeasurementUnit
    form = MeasurementUnitInlineForm
    extra = 0
    show_change_link = True


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


class CloudTableInline(admin.TabularInline):
    model = CloudTable
    extra = 0
    can_delete = False
    show_change_link = True
    readonly_fields = [
        "gcp_project_id",
        "gcp_dataset_id",
        "gcp_table_id",
    ]
    fields = readonly_fields
    template = "admin/cloud_table_inline.html"

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class ObservationLevelInline(OrderedStackedInline):
    model = ObservationLevel
    form = ObservationLevelInlineForm
    extra = 0
    show_change_link = True
    readonly_fields = [
        "entity",
        "order",
        "move_up_down_links",
    ]
    fields = readonly_fields
    template = "admin/observation_level_inline.html"
    ordering = ["order"]

    def get_formset(self, request, obj=None, **kwargs):
        self.parent_obj = obj
        return super().get_formset(request, obj, **kwargs)

    def get_ordering_prefix(self):
        """Return the appropriate ordering prefix based on parent model"""
        if isinstance(self.parent_obj, Table):
            return "table"
        elif isinstance(self.parent_obj, RawDataSource):
            return "rawdatasource"
        elif isinstance(self.parent_obj, InformationRequest):
            return "informationrequest"
        elif isinstance(self.parent_obj, Analysis):
            return "analysis"
        return super().get_ordering_prefix()

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


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
    fields = [
        "units",
    ]


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


class PollInline(admin.StackedInline):
    model = Poll
    form = PollInlineForm
    extra = 0
    fields = [
        "id",
        "entity",
        "frequency",
        "latest",
        "pipeline",
    ]
    autocomplete_fields = [
        "entity",
        "pipeline",
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


def reorder_observation_levels(modeladmin, request, queryset):
    """Reorder observation levels in respect to parent"""
    if "do_action" in request.POST:
        form = ReorderObservationLevelsForm(request.POST)
        if form.is_valid():
            if queryset.count() != 1:
                messages.error(
                    request,
                    "To pass the names manually you must select only one parent.",
                )
                return

            parent = queryset.first()
            ordered_entities = form.cleaned_data["ordered_entities"].split()

            # Get observation levels for this parent
            if hasattr(parent, "observation_levels"):
                obs_levels = parent.observation_levels.all()

                # Create a mapping of entity names to observation levels
                obs_by_entity = {ol.entity.name: ol for ol in obs_levels}

                # Update order based on provided entity names
                for i, entity_name in enumerate(ordered_entities):
                    if entity_name in obs_by_entity:
                        obs_by_entity[entity_name].order = i
                        obs_by_entity[entity_name].save()

                messages.success(request, "Observation levels reordered successfully")
            else:
                messages.error(request, "Selected object has no observation levels")
    else:
        form = ReorderObservationLevelsForm()
        return render(
            request,
            "admin/reorder_observation_levels.html",
            {"title": "Reorder observation levels", "parents": queryset, "form": form},
        )


reorder_observation_levels.short_description = "Alterar ordem dos níveis de observação"


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
        "administrative_level",
        "parent",
    ]
    search_fields = [
        "name",
        "slug",
    ]
    list_filter = [
        AreaAdministrativeLevelFilter,
        AreaParentFilter,
    ]
    autocomplete_fields = [
        "parent",
        "entity",
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
        "spatial_coverage",
        "temporal_coverage",
        "page_views",
        "created_at",
        "updated_at",
    ]
    search_fields = ["name", "slug", "organizations__name"]
    filter_horizontal = [
        "tags",
        "themes",
        "organizations",
    ]
    list_display = [
        "name",
        "get_organizations",
        "temporal_coverage",
        "related_tables",
        "related_raw_data_sources",
        "updated_at",
    ]
    ordering = ["-updated_at"]

    def get_organizations(self, obj):
        """Display all organizations for the dataset"""
        return ", ".join([org.name for org in obj.organizations.all()])

    get_organizations.short_description = "Organizations"

    def related_tables(self, obj):
        return format_html(
            "<a class='related-widget-wrapper-link add-related' "
            "href='/admin/v1/table/add/?dataset={0}&_to_field=id&_popup=1'>{1} {2}</a>",
            obj.id,
            obj.tables.count(),
            "tables" if obj.tables.count() > 1 else "table",
        )

    related_tables.short_description = "Tables"

    def related_raw_data_sources(self, obj):
        return format_html(
            "<a class='related-widget-wrapper-link add-related' "
            "href='/admin/v1/table/add/?dataset={0}&_to_field=id&_popup=1'>{1} {2}</a>",
            obj.id,
            obj.raw_data_sources.count(),
            "sources" if obj.raw_data_sources.count() > 1 else "sources",
        )

    related_raw_data_sources.short_description = "Sources"


class CustomUserAdmin(UserAdmin):
    search_fields = ["username", "first_name", "last_name", "email"]


if User in admin.site._registry:
    admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


class TableAdmin(OrderedInlineModelAdminMixin, TabbedTranslationAdmin):
    form = TableForm
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "dataset",
                    "get_table_url",
                    "status",
                    "name",
                    "slug",
                    "description",
                    "get_datetime_ranges_display",
                    "number_columns",
                    "number_rows",
                    "get_update_display",
                    "raw_data_source",
                    "published_by",
                    "data_cleaned_by",
                    "auxiliary_files_url",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )
    actions = [
        reorder_columns,
        reset_column_order,
        reorder_observation_levels,
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
        "get_table_url",
        "get_datetime_ranges_display",
        "partitions",
        "created_at",
        "updated_at",
        "spatial_coverage",
        "full_temporal_coverage",
        "coverage_datetime_units",
        "number_rows",
        "number_columns",
        "uncompressed_file_size",
        "compressed_file_size",
        "page_views",
        "get_update_display",
    ]
    search_fields = [
        "name",
        "dataset__name",
    ]
    autocomplete_fields = [
        "dataset",
        "published_by",
        "data_cleaned_by",
    ]
    filter_horizontal = [
        "raw_data_source",
    ]
    list_display = [
        "name",
        "dataset",
        "get_publishers",
        "get_data_cleaners",
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

    def get_queryset(self, request):
        """Optimize queryset by prefetching related objects"""
        return super().get_queryset(request).prefetch_related("published_by", "data_cleaned_by")

    def get_publishers(self, obj):
        """Display all publishers for the table"""
        # Convert to list to avoid multiple DB hits
        publishers = list(obj.published_by.all())
        return ", ".join(f"{pub.first_name} {pub.last_name}" for pub in publishers)

    get_publishers.short_description = "Publishers"

    def get_data_cleaners(self, obj):
        """Display all data cleaners for the table"""
        # Convert to list to avoid multiple DB hits
        cleaners = list(obj.data_cleaned_by.all())
        return ", ".join(f"{cleaner.first_name} {cleaner.last_name}" for cleaner in cleaners)

    get_data_cleaners.short_description = "Data Cleaners"

    def get_table_url(self, obj):
        """Get the clickable URL for the table"""
        website_url = f"https://basedosdados.org/dataset/{obj.dataset.id}?table={obj.id}"
        website_html = format_html(
            '<a href="{}" target="_blank">🖥️ Ver tabela no site</a>', website_url
        )

        cloud_tables = obj.cloud_tables.all()

        if len(cloud_tables) == 0:
            add_cloud_table_url = reverse("admin:v1_cloudtable_add") + f"?table={obj.id}"
            gcp_html = format_html(
                'No cloud table found. <a href="{}">Create here</a>', add_cloud_table_url
            )

        elif len(cloud_tables) > 1:
            cloud_table_tab = reverse("admin:v1_table_change") + "/#cloud-tables-tab"
            gcp_html = format_html(
                'More than 1 cloud table found. <a href="{}">Fix it here</a>', cloud_table_tab
            )

        else:
            cloud_table = cloud_tables[0]
            gcp_dev_url = f"https://console.cloud.google.com/bigquery?p=basedosdados-dev&d={cloud_table.gcp_dataset_id}&t={cloud_table.gcp_table_id}&page=table"
            gcp_prod_url = f"https://console.cloud.google.com/bigquery?p=basedosdados&d={cloud_table.gcp_dataset_id}&t={cloud_table.gcp_table_id}&page=table"

            # Gerando o HTML
            gcp_html = format_html(
                '<a href="{}" target="_blank">🧩 Ver tabela em BigQuery-dev</a><br>'
                '<a href="{}" target="_blank">🧊 Ver tabela em BigQuery-prod</a>',
                gcp_dev_url,
                gcp_prod_url,
            )

        return format_html("{}<br>{}", website_html, gcp_html)

    get_table_url.short_description = "Table URLs"

    def get_datetime_ranges_display(self, obj):
        """Display datetime ranges with links to their admin pages"""
        coverages = list(obj.coverages.all())
        links = []

        if len(coverages) == 0:
            add_coverage_url = reverse("admin:v1_coverage_add") + f"?table={obj.id}"
            return format_html("No coverages found. <a href='{}'>Create here</a>", add_coverage_url)

        for cov in coverages:
            url_coverage = reverse("admin:v1_coverage_change", args=[cov.id])
            add_date_time_range_url = reverse("admin:v1_datetimerange_add") + f"?coverage={cov.id}"
            status = "Closed" if cov.is_closed else "Open"

            if cov.datetime_ranges.count() == 0:
                links.append(
                    format_html(
                        "⚠️ <a href='{}'>{} coverage</a> found, but no Datetime Range. <a href='{}'>Create here</a>",
                        add_date_time_range_url,
                        status,
                        add_date_time_range_url,
                    )
                )

            ranges = sorted(cov.datetime_ranges.all(), key=lambda dt: str(dt))
            for dt_range in ranges:
                url_dt_range = reverse("admin:v1_datetimerange_change", args=[dt_range.id])
                links.append(
                    format_html(
                        '<a href="{}">{}</a> -  <a href="{}">{} coverage</a>',
                        url_dt_range,
                        str(dt_range),
                        url_coverage,
                        status,
                    )
                )

        return format_html("<br>".join(links))

    get_datetime_ranges_display.short_description = "DateTime Ranges"

    def get_update_display(self, obj):
        """Display update info"""

        def check_if_there_is_only_one_object_connected(
            object_label, attr_label, tab_label, connection_obj
        ):
            print(f"\t\t\t{object_label = }")
            print(f"\t\t\t{attr_label = }")
            print(f"\t\t\t{tab_label = }")
            print(f"\t\t\t{connection_obj = }")

            campos = [f.name for f in connection_obj._meta.get_fields()]
            print(f"\t\t\t{campos = }")

            if attr_label not in campos:
                print(f"\t\t\t{attr_label} not in {campos}")
                return None, format_html(
                    "No {0} found. <a href='{1}'>Create one</a>",
                    object_label,
                    connection_obj.admin_url,
                )

            obj_list = getattr(connection_obj, attr_label).all()

            print(f"\t\t\t{list(obj_list) = }")

            connection_label = connection_obj._meta.model_name

            print(f"\t\t\t{connection_label = }")

            change_url = connection_obj.admin_url + ("#" + tab_label if tab_label else "")

            print(f"\t\t\t{change_url = }")

            # Se não houver objetos
            if len(obj_list) == 0:
                return None, format_html(
                    "No {0} found. <a href='{1}'>Create one</a>", object_label, change_url
                )

            # Se houver mais de 1 objeto
            elif len(obj_list) > 1:
                return None, format_html(
                    "More than 1 {0} found. <a href='{1}'>Fix it</a>", object_label, change_url
                )

            # Se houver exatamente 1 objeto
            else:
                selected_obj = obj_list[0]
                html = format_html(
                    "<a href='{}'>{}</a> {} found in <a href='{}'>{}</a> ",
                    selected_obj.admin_url,
                    str(selected_obj),
                    object_label,
                    change_url,
                    connection_label,
                )
                return obj_list[0], html

        def check_if_there_is_only_one_raw_data_source_connected(table_object):
            obj_list = getattr(table_object, "raw_data_source").all()
            if len(obj_list) == 0:
                return None, format_html("No Raw Data Source found. Add one in the box bellow")

            # Se houver mais de 1 objeto
            elif len(obj_list) > 1:
                return None, format_html(
                    "More than 1 Raw Data Source found. Fix one in the box bellow"
                )

            # Se houver exatamente 1 objeto
            else:
                selected_obj = obj_list[0]
                html = format_html(
                    "<a href='{}'>Raw Data Source</a> found",
                    selected_obj.admin_url,
                    str(selected_obj),
                )
                return obj_list[0], html

        _, update_html = check_if_there_is_only_one_object_connected(
            "update", "updates", "updates-tab", obj
        )
        (
            raw_data_source_obj,
            raw_data_source_html,
        ) = check_if_there_is_only_one_raw_data_source_connected(obj)
        print(f"{raw_data_source_obj.admin_url = }")
        if raw_data_source_obj:
            _, raw_data_source_update_html = check_if_there_is_only_one_object_connected(
                "update", "updates", "updates-tab", raw_data_source_obj
            )
            print(f"{raw_data_source_update_html = }")
            _, poll_raw_data_source_html = check_if_there_is_only_one_object_connected(
                "poll", "polls", "polls-tab", raw_data_source_obj
            )

        raw_data_source_html = format_html(
            raw_data_source_update_html + "<br>" + poll_raw_data_source_html
        )

        return format_html(update_html + "<br>" + raw_data_source_html)


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


class MeasurementUnitCategoryAdmin(TabbedTranslationAdmin):
    list_display = [
        "slug",
        "name",
    ]
    search_fields = [
        "slug",
        "name",
    ]


class MeasurementUnitAdmin(TabbedTranslationAdmin):
    list_display = [
        "slug",
        "name",
        "tex",
        "category",
    ]
    search_fields = [
        "slug",
        "name",
        "tex",
        "category__name",
    ]
    list_filter = [
        "category",
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
    list_display = [
        "__str__",
        "table",
    ]
    list_filter = [
        "table__dataset__organizations__name",
    ]
    autocomplete_fields = [
        "table",
        "observation_level",
    ]
    readonly_fields = [
        "id",
        "order",
        "spatial_coverage",
        "temporal_coverage",
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


def reset_observation_level_order(modeladmin, request, queryset):
    """Reset observation level order in respect to parent"""
    # Group observation levels by their parent
    by_table = {}
    by_raw_data_source = {}
    by_information_request = {}
    by_analysis = {}

    for obs in queryset:
        if obs.table_id:
            by_table.setdefault(obs.table_id, []).append(obs)
        elif obs.raw_data_source_id:
            by_raw_data_source.setdefault(obs.raw_data_source_id, []).append(obs)
        elif obs.information_request_id:
            by_information_request.setdefault(obs.information_request_id, []).append(obs)
        elif obs.analysis_id:
            by_analysis.setdefault(obs.analysis_id, []).append(obs)

    # Reset order within each parent group
    for parent_levels in [by_table, by_raw_data_source, by_information_request, by_analysis]:
        for levels in parent_levels.values():
            sorted_levels = sorted(levels, key=lambda x: x.entity.name)
            for i, obs_level in enumerate(sorted_levels):
                obs_level.order = i
                obs_level.save()


reset_observation_level_order.short_description = "Reiniciar ordem dos níveis de observação"


class ObservationLevelAdmin(admin.ModelAdmin):
    actions = [reset_observation_level_order]
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
        "table",
        "raw_data_source",
        "information_request",
    ]
    list_display = [
        "__str__",
        "table",
        "raw_data_source",
        "information_request",
    ]


class RawDataSourceAdmin(OrderedInlineModelAdminMixin, TabbedTranslationAdmin):
    actions = [
        reorder_observation_levels,
    ]
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
    inlines = [
        CoverageInline,
        UpdateInline,
        ObservationLevelInline,
        PollInline,
    ]


class InformationRequestAdmin(OrderedInlineModelAdminMixin, TabbedTranslationAdmin):
    actions = [
        reorder_observation_levels,
    ]
    list_display = ["__str__", "dataset", "created_at", "updated_at"]
    search_fields = ["__str__", "dataset__name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    autocomplete_fields = ["dataset"]
    inlines = [
        CoverageInline,
        ObservationLevelInline,
        PollInline,
    ]


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


class UnitsInline(admin.TabularInline):
    model = DateTimeRange.units.through
    extra = 0
    fields = ["column"]
    raw_id_fields = ["column"]
    verbose_name = "Unit"
    verbose_name_plural = "Units"


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
        "units",
    ]

    inlines = [UnitsInline]
    raw_id_fields = ["coverage"]


class CoverageAdmin(admin.ModelAdmin):
    readonly_fields = ["id", "datetime_ranges_display"]
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

    def datetime_ranges_display(self, obj):
        """Display datetime ranges with links to their admin pages"""
        ranges = obj.datetime_ranges.all()
        links = []
        for dt_range in ranges:
            url = reverse("admin:v1_datetimerange_change", args=[dt_range.id])
            links.append(format_html('<a href="{}">{}</a>', url, str(dt_range)))

        # Add link to add new datetime range
        add_url = reverse("admin:v1_datetimerange_add") + f"?coverage={obj.id}"
        links.append(mark_safe(f'<a class="addlink" href="{add_url}">Add DateTime Range</a>'))

        return mark_safe("<br>".join(links))

    datetime_ranges_display.short_description = "DateTime Ranges"

    def get_queryset(self, request):
        """Optimize queryset by prefetching related objects"""
        qs = (
            super()
            .get_queryset(request)
            .select_related("table", "column", "raw_data_source", "information_request", "area")
        )
        # Add prefetch for datetime_ranges and their units
        return qs.prefetch_related("datetime_ranges", "datetime_ranges__units")


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
    actions = [
        reorder_observation_levels,
    ]
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


class PollAdmin(admin.ModelAdmin):
    readonly_fields = [
        "id",
    ]
    search_fields = [
        "entity__name",
        "raw_data_source__name",
        "information_request__dataset__name",
    ]
    autocomplete_fields = [
        "entity",
        "pipeline",
        "raw_data_source",
        "information_request",
    ]
    list_filter = [
        "entity__category__name",
    ]
    list_display = [
        "__str__",
        "raw_data_source",
        "information_request",
    ]


class PipelineAdmin(admin.ModelAdmin):
    readonly_fields = [
        "id",
    ]
    search_fields = [
        "id",
        "github_url",
    ]
    list_display = [
        "id",
        "github_url",
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
admin.site.register(MeasurementUnit, MeasurementUnitAdmin)
admin.site.register(MeasurementUnitCategory, MeasurementUnitCategoryAdmin)
admin.site.register(ObservationLevel, ObservationLevelAdmin)
admin.site.register(Organization, OrganizationAdmin)
admin.site.register(Pipeline, PipelineAdmin)
admin.site.register(RawDataSource, RawDataSourceAdmin)
admin.site.register(Status, StatusAdmin)
admin.site.register(Table, TableAdmin)
admin.site.register(TableNeighbor, TableNeighborAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Theme, ThemeAdmin)
admin.site.register(Update, UpdateAdmin)
admin.site.register(QualityCheck, QualityCheckAdmin)
admin.site.register(Poll, PollAdmin)
