# -*- coding: utf-8 -*-
from django import forms


class ReorderTablesForm(forms.Form):
    ordered_slugs = forms.CharField(widget=forms.Textarea)
