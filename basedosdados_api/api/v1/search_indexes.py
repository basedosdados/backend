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
    table_ids = indexes.MultiValueField(model_attr="tables__id", null=True)
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
    raw_data_sources = indexes.MultiValueField(
        model_attr="raw_data_sources__id", null=True
    )
    information_requests = indexes.MultiValueField(
        model_attr="information_requests__id", null=True
    )
    is_closed = indexes.BooleanField(model_attr="is_closed")

    def get_model(self):
        return Dataset

    def index_queryset(self, using=None):
        return self.get_model().objects.all()

    def prepare(self, obj):
        data = super().prepare(obj)
        # table ids
        table_ids = data.get("table_ids", [])
        data["first_table_id"] = table_ids[0] if table_ids else ""
        if table_ids:
            data["n_bdm_tables"] = len(table_ids)

        # Raw data sources (renamed to "original sources")
        raw_data_sources = data.get("raw_data_sources", [])
        data["first_original_source_id"] = (
            raw_data_sources[0] if raw_data_sources else ""
        )
        if raw_data_sources:
            data["n_original_sources"] = len(raw_data_sources)
        else:
            data["n_original_sources"] = 0
        # Information requests (renamed to "lai")
        information_requests = data.get("information_requests", [])
        data["first_lai_id"] = information_requests[0] if information_requests else ""
        if information_requests:
            data["n_lais"] = len(information_requests)
        else:
            data["n_lais"] = 0
        return data
