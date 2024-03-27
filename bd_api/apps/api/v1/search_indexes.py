# -*- coding: utf-8 -*-
from haystack import indexes

from bd_api.apps.api.v1.models import Dataset


class DatasetIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)

    organization_slug = indexes.CharField(model_attr="organization__slug", null=True)
    organization_name = indexes.CharField(model_attr="organization__name", null=True)
    organization_description = indexes.CharField(model_attr="organization__description", null=True)

    dataset_slug = indexes.CharField(model_attr="slug", null=True)
    dataset_name = indexes.CharField(model_attr="name", null=True)
    dataset_description = indexes.CharField(model_attr="description", null=True)

    table_slugs = indexes.MultiValueField(model_attr="tables__slug", null=True)
    table_names = indexes.MultiValueField(model_attr="tables__name", null=True)
    table_descriptions = indexes.MultiValueField(model_attr="tables__description", null=True)

    tag_names = indexes.MultiValueField(model_attr="tags__name", null=True)
    tag_slugs = indexes.MultiValueField(model_attr="tags__slug", null=True, faceted=True)

    theme_names = indexes.MultiValueField(model_attr="themes__name", null=True)
    theme_slugs = indexes.MultiValueField(model_attr="themes__slug", null=True, faceted=True)

    def get_model(self):
        return Dataset
