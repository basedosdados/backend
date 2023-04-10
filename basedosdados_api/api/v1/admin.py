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


class CoverageAdmin(admin.ModelAdmin):
    readonly_fields = ["id"]
    list_display = ["area", "coverage_type", "table"]


class DateTimeRangeAdmin(admin.ModelAdmin):
    readonly_fields = ["id"]
    list_display = ["__str__", "coverage"]


admin.site.register(Organization, OrganizationAdmin)
admin.site.register(Dataset, DatasetAdmin)
admin.site.register(Table, TableAdmin)
admin.site.register(InformationRequest)
admin.site.register(RawDataSource)
admin.site.register(BigQueryType)
admin.site.register(Column)
admin.site.register(CloudTable)
admin.site.register(Area)
admin.site.register(Theme)
admin.site.register(Tag)
admin.site.register(Coverage, CoverageAdmin)
admin.site.register(Status)
admin.site.register(Update)
admin.site.register(Availability)
admin.site.register(License)
admin.site.register(Language)
admin.site.register(ObservationLevel)
admin.site.register(Entity)
admin.site.register(EntityCategory)
admin.site.register(Dictionary)
admin.site.register(Pipeline)
admin.site.register(AnalysisType)
admin.site.register(DateTimeRange, DateTimeRangeAdmin)
admin.site.register(Key)
