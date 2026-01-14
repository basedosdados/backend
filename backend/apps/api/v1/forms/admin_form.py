# -*- coding: utf-8 -*-
from django import forms

from backend.apps.api.v1.models import (
    CloudTable,
    Column,
    ColumnOriginalName,
    Coverage,
    MeasurementUnit,
    ObservationLevel,
    Poll,
    RawDataSource,
    Table,
    Update,
)


class UUIDHiddenIdForm(forms.ModelForm):
    """Form to include UUID in inline formes (Table, Column and Coverage)"""

    id = forms.UUIDField(widget=forms.HiddenInput(), required=False)

    class Meta:
        """Meta class"""

        abstract = True


class TableForm(forms.ModelForm):
    class Meta:
        model = Table
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            # Check both the saved instance and current form data
            dataset_id = self.instance.dataset_id
            if not dataset_id and self.data:
                dataset_id = self.data.get("dataset")

            if dataset_id:
                self.fields["raw_data_source"].queryset = RawDataSource.objects.filter(
                    dataset_id=dataset_id
                )
            else:
                self.fields["raw_data_source"].queryset = RawDataSource.objects.none()


class TableInlineForm(UUIDHiddenIdForm):
    class Meta(UUIDHiddenIdForm):
        model = Table
        fields = [
            "id",
            "slug",
            "name",
        ]
        readonly_fields = [
            "order",
            "move_up_down_links",
        ]


class MeasurementUnitInlineForm(UUIDHiddenIdForm):
    class Meta(UUIDHiddenIdForm.Meta):
        model = MeasurementUnit
        fields = "__all__"


class ColumnInlineForm(UUIDHiddenIdForm):
    class Meta(UUIDHiddenIdForm.Meta):
        model = Column
        fields = [
            "id",
            "name",
            "bigquery_type",
            "description",
            "covered_by_dictionary",
            "observation_level",
            "directory_primary_key",
            "is_primary_key",
        ]
        readonly_fields = [
            "order",
            "move_up_down_links",
        ]


class ColumnOriginalNameInlineForm(UUIDHiddenIdForm):
    class Meta(UUIDHiddenIdForm.Meta):
        model = ColumnOriginalName
        fields = "__all__"


class CloudTableInlineForm(UUIDHiddenIdForm):
    class Meta(UUIDHiddenIdForm.Meta):
        model = CloudTable
        fields = "__all__"


class ObservationLevelInlineForm(UUIDHiddenIdForm):
    class Meta(UUIDHiddenIdForm.Meta):
        model = ObservationLevel
        fields = [
            "id",
            "entity",
            "table",
            "raw_data_source",
            "information_request",
            "analysis",
        ]
        readonly_fields = [
            "order",
            "move_up_down_links",
        ]


class CoverageInlineForm(UUIDHiddenIdForm):
    class Meta(UUIDHiddenIdForm.Meta):
        model = Coverage
        fields = [
            "id",
            "area",
            "is_closed",
        ]


class UpdateInlineForm(UUIDHiddenIdForm):
    class Meta(UUIDHiddenIdForm.Meta):
        model = Update
        fields = "__all__"


class PollInlineForm(forms.ModelForm):
    class Meta:
        model = Poll
        fields = [
            "entity",
            "frequency",
            "latest",
        ]
