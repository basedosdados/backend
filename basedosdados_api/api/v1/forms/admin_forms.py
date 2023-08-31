# -*- coding: utf-8 -*-
from django import forms

from basedosdados_api.api.v1.models import (
    Column,
    Coverage,
    ObservationLevel,
    Table,
    UUIDHIddenIdForm,
)


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
            "is_closed",
        ]
        readonly_fields = [
            "order",
            "move_up_down_links",
        ]


class ColumnInlineForm(UUIDHIddenIdForm):
    class Meta(UUIDHIddenIdForm.Meta):
        model = Column
        fields = [
            "id",
            "name",
            "name_staging",
            "description",
            "bigquery_type",
            "is_closed",
            "status",
            "is_primary_key",
            "table",
        ]
        readonly_fields = [
            "order",
            "move_up_down_links",
        ]


class ObservationLevelForm(forms.ModelForm):
    column_choice = forms.ModelChoiceField(queryset=Column.objects.all())

    class Meta:
        model = ObservationLevel
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial["column_choice"] = self.instance.columns.first()


class CoverageInlineForm(UUIDHIddenIdForm):
    class Meta(UUIDHIddenIdForm.Meta):
        model = Coverage
        fields = [
            "id",
            "area",
            "table",
        ]
