# -*- coding: utf-8 -*-
from django.contrib import admin
from modeltranslation.admin import (
    TabbedTranslationAdmin,
    TranslationStackedInline,
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
    AnalysisType,
    DateTimeRange,
    Key, UUIDHIddenIdForm,
)


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
            "is_closed"
        ]


class ColumnInlineForm(UUIDHIddenIdForm):
    class Meta(UUIDHIddenIdForm.Meta):
        model = Column
        fields = [
            "id",
            "name",
            "description",
            "bigquery_type",
            "is_closed",
            "table",
        ]


# Inlines

class ColumnInline(TranslationStackedInline):
    model = Column
    form = ColumnInlineForm
    extra = 0
    show_change_link = True
    show_full_result_count = True
    autocomplete_fields = [
        "directory_primary_key",
        "observation_level",
    ]


class TableInline(TranslationStackedInline):
    model = Table
    form = TableInlineForm
    extra = 0
    show_change_link = True


# Filters

class OrganizationImageFilter(admin.SimpleListFilter):
    title = "has_picture"
    parameter_name = "has_picture"

    def lookups(self, request, model_admin):
        return (
            ("True", "Yes"),
            ("False", "No"),
        )

    def queryset(self, request, queryset):
        if self.value() == "True":
            return queryset.exclude(picture="")
        if self.value() == "False":
            return queryset.filter(picture="")


# Model Admins
class AreaAdmin(TabbedTranslationAdmin):
    readonly_fields = ["id", ]
    list_display = ["name", "slug", ]
    search_fields = ["name", "slug", ]


class OrganizationAdmin(TabbedTranslationAdmin):
    readonly_fields = ["id", "created_at", "updated_at"]
    list_display = ["name", "has_picture"]
    search_fields = ["name", "slug"]
    list_filter = [OrganizationImageFilter, "created_at", "updated_at"]
    autocomplete_fields = ["area", ]


class ThemeAdmin(TabbedTranslationAdmin):
    readonly_fields = ["id", "created_at", "updated_at"]
    list_display = ["name", "slug", ]
    search_fields = ["name", "slug", ]


class TagAdmin(TabbedTranslationAdmin):
    readonly_fields = ["id", "created_at", "updated_at"]
    list_display = ["name", "slug", ]
    search_fields = ["name", "slug", ]


class DatasetAdmin(TabbedTranslationAdmin):
    readonly_fields = ["id", "full_slug", "created_at", "updated_at"]
    list_display = ["name", "full_slug", "organization"]
    search_fields = ["name", "slug", "organization__name"]
    inlines = [TableInline, ]
    filter_horizontal = ["tags", "themes", ]
    list_filter = ["organization__name", ]


class TableAdmin(TabbedTranslationAdmin):
    readonly_fields = ["id", "created_at", "updated_at"]
    search_fields = ["name", "dataset__name"]
    inlines = [ColumnInline, ]
    autocomplete_fields = [
        "dataset",
        "partner_organization",
        "published_by",
        "data_cleaned_by",
    ]


class ColumnAdmin(TabbedTranslationAdmin):
    readonly_fields = ["id", ]
    list_display = ["__str__", "table", ]
    search_fields = ["name", "table__name"]
    autocomplete_fields = [
        "table",
        "observation_level",
        "directory_primary_key"
    ]


class ObservationLevelAdmin(admin.ModelAdmin):
    readonly_fields = ["id",]
    search_fields = ["name", "entity__name"]
    autocomplete_fields = [
        "entity",
        "table",
        "raw_data_source",
        "information_request",
    ]
    list_filter = ["entity__category__name", ]
    list_display = ["__str__", "table", "raw_data_source", "information_request", ]
    inlines = [ColumnInline, ]


class RawDataSourceAdmin(admin.ModelAdmin):
    readonly_fields = ["id", "created_at", "updated_at"]
    list_display = ["name", "dataset", "created_at", "updated_at"]
    search_fields = ["name", "dataset__name"]
    autocomplete_fields = ["dataset", "languages", ]
    filter_horizontal = ["languages", "area_ip_address_required", ]


class InformationRequestAdmin(TabbedTranslationAdmin):
    readonly_fields = ["id", "created_at", "updated_at"]
    list_display = ["__str__", "dataset", "created_at", "updated_at"]
    search_fields = ["__str__", "dataset__name"]
    autocomplete_fields = ["dataset", ]


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
    autocomplete_fields = ["coverage", ]


class CoverageAdmin(admin.ModelAdmin):
    readonly_fields = ["id"]
    list_display = ["area", "coverage_type", "table"]
    list_filter = [CoverageTypeAdminFilter,]
    autocomplete_fields = ["table", "raw_data_source", "information_request", "column", ]
    search_fields = ["table__name", "raw_data_source__name", "information_request__dataset__name", "column__name", ]
    inlines = [DateTimeRangeInline, ]


class EntityCategoryAdmin(TabbedTranslationAdmin):
    readonly_fields = ["id", ]
    list_display = ["name", "slug", ]
    search_fields = ["name", "slug", ]


class EntityAdmin(TabbedTranslationAdmin):
    readonly_fields = ["id", ]
    list_display = ["name", "category", ]
    search_fields = ["name", "category__name"]
    list_filter = ["category", ]
    autocomplete_fields = ["category", ]


class LanguageAdmin(TabbedTranslationAdmin):
    readonly_fields = ["id", ]
    list_display = ["name", "slug", ]
    search_fields = ["name", "slug", ]


class UpdateAdmin(admin.ModelAdmin):
    readonly_fields = ["id", ]
    list_display = ["__str__",]
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
    readonly_fields = ["id", ]
    list_display = ["name", "slug", ]
    search_fields = ["name", "slug", ]


class AvailabilityAdmin(TabbedTranslationAdmin):
    readonly_fields = ["id", ]
    list_display = ["name", "slug", ]
    search_fields = ["name", "slug", ]


class CloudTableAdmin(admin.ModelAdmin):
    readonly_fields = ["id", ]
    list_display = ["__str__", ]
    search_fields = ["table", "gcp_project_id", "gcp_dataset_id", "gcp_table_id", ]
    autocomplete_fields = ["table", "columns"]
    filter_horizontal = ["columns", ]


class StatusAdmin(TabbedTranslationAdmin):
    readonly_fields = ["id", ]
    list_display = ["name", "slug", ]
    search_fields = ["name", "slug", ]


admin.site.register(AnalysisType)
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
admin.site.register(Key)
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
