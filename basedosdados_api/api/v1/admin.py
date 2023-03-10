# -*- coding: utf-8 -*-
from django.contrib import admin

from basedosdados_api.api.v1.models import (
    Organization,
    Dataset,
    Table,
    InformationRequest,
    RawDataSource,
    BigQueryTypes,
    Column,
    CloudTable,
    Area,
    Theme,
    Tag,
    Coverage,
    Status,
    UpdateFrequency,
    Availability,
    License,
    Language,
    ObservationLevel,
    Entity,
    Dictionary,
    Pipeline,
    AnalysisType,
    DateTimeRange,
)


class DatasetAdmin(admin.ModelAdmin):
    readonly_fields = ["id", "created_at", "updated_at"]


class TableAdmin(admin.ModelAdmin):
    readonly_fields = ["id", "created_at", "updated_at"]


class CoverageAdmin(admin.ModelAdmin):
    readonly_fields = ["id"]
    list_display = ["area", "coverage_type", "table"]


class DateTimeRangeAdmin(admin.ModelAdmin):
    readonly_fields = ["id"]
    list_display = ["__str__", "coverage"]


admin.site.register(Organization)
admin.site.register(Dataset, DatasetAdmin)
admin.site.register(Table, TableAdmin)
admin.site.register(InformationRequest)
admin.site.register(RawDataSource)
admin.site.register(BigQueryTypes)
admin.site.register(Column)
admin.site.register(CloudTable)
admin.site.register(Area)
admin.site.register(Theme)
admin.site.register(Tag)
admin.site.register(Coverage, CoverageAdmin)
admin.site.register(Status)
admin.site.register(UpdateFrequency)
admin.site.register(Availability)
admin.site.register(License)
admin.site.register(Language)
admin.site.register(ObservationLevel)
admin.site.register(Entity)
admin.site.register(Dictionary)
admin.site.register(Pipeline)
admin.site.register(AnalysisType)
admin.site.register(DateTimeRange, DateTimeRangeAdmin)
