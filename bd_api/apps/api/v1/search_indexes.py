# -*- coding: utf-8 -*-
from haystack import indexes

from bd_api.apps.api.v1.models import Dataset


class DatasetIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)

    dataset = indexes.CharField(model_attr="slug", null=True, faceted=True)
    dataset_name = indexes.CharField(model_attr="name", null=True)
    dataset_description = indexes.CharField(model_attr="description", null=True)

    table = indexes.MultiValueField(model_attr="tables__slug", null=True, faceted=True)
    table_names = indexes.MultiValueField(model_attr="tables__name", null=True)
    table_descriptions = indexes.MultiValueField(model_attr="tables__description", null=True)

    organization = indexes.CharField(model_attr="organization__slug", null=True, faceted=True)
    organization_names = indexes.CharField(model_attr="organization__name", null=True)
    organization_descriptions = indexes.CharField(model_attr="organization__description", null=True)

    tag = indexes.MultiValueField(model_attr="tags__slug", null=True, faceted=True)
    tag_names = indexes.MultiValueField(model_attr="tags__name", null=True)

    theme = indexes.MultiValueField(model_attr="themes__slug", null=True, faceted=True)
    theme_names = indexes.MultiValueField(model_attr="themes__name", null=True)

    entity = indexes.MultiValueField(
        model_attr="tables__observation_levels__entity__slug", null=True, faceted=True
    )
    entity_names = indexes.MultiValueField(
        model_attr="tables__observation_levels__entity__name", null=True, faceted=True
    )

    contains_open_data = indexes.BooleanField(model_attr="contains_open_data")
    contains_closed_data = indexes.BooleanField(model_attr="contains_closed_data")

    contains_tables = indexes.BooleanField(model_attr="contains_tables")
    contains_raw_data_sources = indexes.BooleanField(model_attr="contains_raw_data_sources")
    contains_information_requests = indexes.BooleanField(model_attr="contains_information_requests")

    def get_model(self):
        return Dataset

    def index_queryset(self, using=None):
        return self.get_model().objects.exclude(status__slug="under_review").all()
