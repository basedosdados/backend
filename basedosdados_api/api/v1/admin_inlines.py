# -*- coding: utf-8 -*-
from django.contrib import admin
from django.forms.models import BaseInlineFormSet
from modeltranslation.admin import TranslationStackedInline
from ordered_model.admin import OrderedStackedInline

from basedosdados_api.api.v1.forms.admin_forms import (
    ColumnInlineForm,
    CoverageInlineForm,
    ObservationLevelForm,
    TableInlineForm,
)
from basedosdados_api.api.v1.models import (
    Column,
    Coverage,
    DateTimeRange,
    InformationRequest,
    ObservationLevel,
    RawDataSource,
    Table,
)


class TranslateOrderedInline(OrderedStackedInline, TranslationStackedInline):
    pass


# Inlines


class CustomObservationLevelInlineFormset(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        columns_queryset = Column.objects.filter(table=self.instance)
        print("Columns queryset: ", columns_queryset)

        for form in self.forms:
            print("Form fields: ", form.fields)
            form.fields["column_choice"].queryset = columns_queryset


class ObservationLevelInline(admin.StackedInline):
    model = ObservationLevel
    form = ObservationLevelForm
    formset = CustomObservationLevelInlineFormset
    template = "admin/edit_inline/stacked_table_observation_level.html"
    extra = 0
    fields = [
        "entity",
        # "column_choice",
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
