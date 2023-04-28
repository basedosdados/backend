# -*- coding: utf-8 -*-
from django.contrib import admin

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
    Key,
)


class DatasetAdmin(admin.ModelAdmin):
    readonly_fields = ["id", "full_slug", "created_at", "updated_at"]
    list_display = ["__str__", "full_slug", "organization"]


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


class OrganizationAdmin(admin.ModelAdmin):
    readonly_fields = ["id", "created_at", "updated_at"]
    list_display = ["name", "has_picture"]
    search_fields = ["name", "slug"]
    list_filter = [OrganizationImageFilter, "created_at", "updated_at"]


class TableAdmin(admin.ModelAdmin):
    readonly_fields = ["id", "created_at", "updated_at"]
    search_fields = ["name", "dataset__name"]


class ColumnAdmin(admin.ModelAdmin):
    readonly_fields = ["id", ]
    list_display = ["__str__", "table", ]
    search_fields = ["name", "table__name"]
    autocomplete_fields = ["table", "observation_level", "directory_primary_key"]


class ObservationLevelAdmin(admin.ModelAdmin):
    readonly_fields = ["id",]
    search_fields = ["name", "entity__name"]


class RawDataSourceAdmin(admin.ModelAdmin):
    readonly_fields = ["id", "created_at", "updated_at"]
    list_display = ["name", "dataset", "created_at", "updated_at"]
    search_fields = ["name", "dataset__name"]


class InformationRequestAdmin(admin.ModelAdmin):
    readonly_fields = ["id", "created_at", "updated_at"]
    list_display = ["__str__", "dataset", "created_at", "updated_at"]
    search_fields = ["__str__", "dataset__name"]


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


admin.site.register(AnalysisType)
admin.site.register(Area)
admin.site.register(Availability)
admin.site.register(BigQueryType)
admin.site.register(CloudTable)
admin.site.register(Column, ColumnAdmin)
admin.site.register(Coverage, CoverageAdmin)
admin.site.register(Dataset, DatasetAdmin)
admin.site.register(DateTimeRange, DateTimeRangeAdmin)
admin.site.register(Dictionary)
admin.site.register(Entity)
admin.site.register(EntityCategory)
admin.site.register(InformationRequest, InformationRequestAdmin)
admin.site.register(Key)
admin.site.register(Language)
admin.site.register(License)
admin.site.register(ObservationLevel, ObservationLevelAdmin)
admin.site.register(Organization, OrganizationAdmin)
admin.site.register(Pipeline)
admin.site.register(RawDataSource, RawDataSourceAdmin)
admin.site.register(Status)
admin.site.register(Table, TableAdmin)
admin.site.register(Tag)
admin.site.register(Theme)
admin.site.register(Update)
