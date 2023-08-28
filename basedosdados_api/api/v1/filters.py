# -*- coding: utf-8 -*-
from django.contrib import admin

from basedosdados_api.api.v1.models import Column, Coverage, ObservationLevel


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


class TableCoverageFilter(admin.SimpleListFilter):
    title = "Coverage"
    parameter_name = "table_coverage"

    def lookups(self, request, model_admin):
        distinct_values = (
            Coverage.objects.filter(table__id__isnull=False)
            .order_by("area__name")
            .distinct()
            .values("area__name", "area__slug")
        )
        # Create a tuple of tuples with the format (value, label).
        return [(value.get("area__slug"), value.get("area__name")) for value in distinct_values]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(coverages__area__slug=self.value())


class TableObservationFilter(admin.SimpleListFilter):
    title = "Observation Level"
    parameter_name = "table_observation"

    def lookups(self, request, model_admin):
        distinct_values = (
            ObservationLevel.objects.filter(table__id__isnull=False)
            .order_by("entity__name")
            .distinct()
            .values("entity__id", "entity__name")
        )
        # Create a tuple of tuples with the format (value, label).
        return [(value.get("entity__id"), value.get("entity__name")) for value in distinct_values]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(observation_levels__entity=self.value())


class DirectoryPrimaryKeyAdminFilter(admin.SimpleListFilter):
    title = "directory_primary_key"
    parameter_name = "directory_primary_key"

    def lookups(self, request, model_admin):
        distinct_values = (
            Column.objects.filter(directory_primary_key__id__isnull=False)
            .order_by("directory_primary_key__name")
            .distinct()
            .values(
                "directory_primary_key__name",
            )
        )
        # Create a tuple of tuples with the format (value, label).
        return [(value.get("directory_primary_key__name"),) for value in distinct_values]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(directory_primary_key__name=self.value())
