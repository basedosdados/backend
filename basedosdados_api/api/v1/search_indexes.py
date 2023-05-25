# -*- coding: utf-8 -*-
from haystack import indexes
from .models import (
    Dataset,
)


class DatasetIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    slug = indexes.CharField(model_attr="slug")
    name = indexes.CharField(model_attr="name")
    description = indexes.CharField(model_attr="description", null=True)
    organization_slug = indexes.CharField(model_attr="organization__slug")
    organization_name = indexes.CharField(model_attr="organization__name")
    organization_description = indexes.CharField(
        model_attr="organization__description", null=True
    )
    organization_picture = indexes.CharField(model_attr="organization__picture")
    table_slugs = indexes.MultiValueField(model_attr="tables__slug", null=True)
    table_names = indexes.MultiValueField(model_attr="tables__name", null=True)
    table_descriptions = indexes.MultiValueField(
        model_attr="tables__description", null=True
    )
    column_names = indexes.MultiValueField(
        model_attr="tables__columns__name", null=True
    )
    column_descriptions = indexes.MultiValueField(
        model_attr="tables__columns__description", null=True
    )
    themes_name = indexes.MultiValueField(model_attr="themes__name", null=True)
    themes_slug = indexes.MultiValueField(model_attr="themes__slug", null=True)
    tags_name = indexes.MultiValueField(model_attr="tags__name", null=True)
    tags_slug = indexes.MultiValueField(model_attr="tags__slug", null=True)
    coverage = indexes.MultiValueField(model_attr="coverage", null=True)
    is_closed = indexes.BooleanField(model_attr="is_closed")

    def get_model(self):
        return Dataset

    def index_queryset(self, using=None):
        return self.get_model().objects.all()
