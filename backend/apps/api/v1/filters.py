# -*- coding: utf-8 -*-
from django.contrib import admin
from django.utils.translation import gettext_lazy

from backend.apps.api.v1.models import Area, Coverage, ObservationLevel, Organization


class OrganizationImageListFilter(admin.SimpleListFilter):
    title = "Picture"
    parameter_name = "has_picture"

    def lookups(self, request, model_admin):
        return (
            ("true", "Yes"),
            ("false", "No"),
        )

    def queryset(self, request, queryset):
        if self.value() == "true":
            return queryset.exclude(picture="")
        if self.value() == "false":
            return queryset.filter(picture="")


class DatasetOrganizationListFilter(admin.SimpleListFilter):
    title = "Organization"
    parameter_name = "organization"

    def lookups(self, request, model_admin):
        organizations = Organization.objects.all().order_by("slug")
        return [(org.id, org.name) for org in organizations]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(organizations__id=self.value())
        return queryset


class TableOrganizationListFilter(admin.SimpleListFilter):
    title = "Organization"
    parameter_name = "organization"

    def lookups(self, request, model_admin):
        values = Organization.objects.order_by("name").distinct().values("name", "pk")
        return [(v.get("pk"), v.get("name")) for v in values]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(dataset__organization=self.value())


class TableCoverageListFilter(admin.SimpleListFilter):
    title = "Coverage"
    parameter_name = "table_coverage"

    def lookups(self, request, model_admin):
        values = (
            Coverage.objects.filter(table__id__isnull=False)
            .order_by("area__name")
            .distinct()
            .values("area__name", "area__slug")
        )
        return [(v.get("area__slug"), v.get("area__name")) for v in values]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(coverages__area__slug=self.value())


class TableObservationListFilter(admin.SimpleListFilter):
    title = "Observation Level"
    parameter_name = "table_observation"

    def lookups(self, request, model_admin):
        distinct_values = (
            ObservationLevel.objects.filter(table__id__isnull=False)
            .order_by("entity__name")
            .distinct()
            .values("entity__id", "entity__name")
        )
        return [(value.get("entity__id"), value.get("entity__name")) for value in distinct_values]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(observation_levels__entity=self.value())


class TableDirectoryListFilter(admin.SimpleListFilter):
    title = gettext_lazy("Directory")
    parameter_name = "is_directory"

    def lookups(self, request, model_admin):
        return (
            ("true", gettext_lazy("Yes")),
            ("false", gettext_lazy("No")),
        )

    def queryset(self, request, queryset):
        if self.value() == "true":
            return queryset.filter(is_directory=True)
        if self.value() == "false":
            return queryset.filter(is_directory=False)


class AreaAdministrativeLevelFilter(admin.SimpleListFilter):
    title = "Administrative Level"
    parameter_name = "administrative_level"

    def lookups(self, request, model_admin):
        return [
            (0, "0"),
            (1, "1"),
            (2, "2"),
            (3, "3"),
            (4, "4"),
            (5, "5"),
        ]

    def queryset(self, request, queryset):
        if self.value() is not None:
            return queryset.filter(administrative_level=self.value())


class AreaParentFilter(admin.SimpleListFilter):
    title = "Parent Area"
    parameter_name = "parent"

    def lookups(self, request, model_admin):
        # Get all areas that have children, ordered by name
        parents = Area.objects.filter(children__isnull=False).distinct().order_by("name")
        return [(area.id, f"{area.name}") for area in parents]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(parent_id=self.value())
