# -*- coding: utf-8 -*-
# forms.py

from django import forms


class ReorderColumnsForm(forms.Form):
    ordered_columns = forms.CharField(
        label="Enter the ordered column names, separated by spaces",
        widget=forms.Textarea,
        required=False,
    )
    use_database_order = forms.BooleanField(
        label="Use the order of the columns in Google BigQuery",
        required=False,
    )
