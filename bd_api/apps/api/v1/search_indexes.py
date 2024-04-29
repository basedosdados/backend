# -*- coding: utf-8 -*-
from haystack import indexes

from bd_api.apps.api.v1.models import Dataset


class DatasetIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)

    updated_at = indexes.DateTimeField(model_attr="updated_at")

    dataset_id = indexes.CharField(
        model_attr="pk",
        indexed=False,
    )
    dataset_slug = indexes.CharField(
        model_attr="slug",
        indexed=False,
    )
    dataset_name = indexes.CharField(
        model_attr="name",
        indexed=False,
    )
    dataset_description = indexes.CharField(
        model_attr="description",
        default="",
        indexed=False,
    )

    table_id = indexes.MultiValueField(
        model_attr="tables__pk",
        indexed=False,
    )
    table_slug = indexes.MultiValueField(
        model_attr="tables__slug",
        indexed=False,
    )
    table_name = indexes.MultiValueField(
        model_attr="tables__name",
        indexed=False,
    )
    table_description = indexes.MultiValueField(
        model_attr="tables__description",
        default="",
        indexed=False,
    )

    organization_id = indexes.MultiValueField(
        model_attr="organization__pk",
        faceted=True,
        indexed=False,
    )
    organization_slug = indexes.MultiValueField(
        model_attr="organization__slug",
        faceted=True,
        indexed=False,
    )
    organization_name = indexes.MultiValueField(
        model_attr="organization__name",
        indexed=False,
    )
    organization_picture = indexes.MultiValueField(
        model_attr="organization__picture",
        default="",
        indexed=False,
    )
    organization_website = indexes.MultiValueField(
        model_attr="organization__website",
        default="",
        indexed=False,
    )
    organization_description = indexes.MultiValueField(
        model_attr="organization__description",
        default="",
        indexed=False,
    )

    tag_slug = indexes.MultiValueField(
        model_attr="tags__slug",
        default="",
        faceted=True,
        indexed=False,
    )
    tag_name = indexes.MultiValueField(
        model_attr="tags__name",
        default="",
        indexed=False,
    )

    theme_slug = indexes.MultiValueField(
        model_attr="themes__slug",
        default="",
        faceted=True,
        indexed=False,
    )
    theme_name = indexes.MultiValueField(
        model_attr="themes__name",
        default="",
        indexed=False,
    )

    entity_slug = indexes.MultiValueField(
        model_attr="tables__observation_levels__entity__slug",
        default="",
        faceted=True,
        indexed=False,
    )
    entity_name = indexes.MultiValueField(
        model_attr="tables__observation_levels__entity__name",
        default="",
        faceted=True,
        indexed=False,
    )

    temporal_coverage = indexes.MultiValueField(
        default="",
        model_attr="coverage",
        indexed=False,
    )

    contains_open_data = indexes.BooleanField(
        model_attr="contains_open_data",
        indexed=False,
    )
    contains_closed_data = indexes.BooleanField(
        model_attr="contains_closed_data",
        indexed=False,
    )

    contains_tables = indexes.BooleanField(
        model_attr="contains_tables",
        indexed=False,
    )
    contains_raw_data_sources = indexes.BooleanField(
        model_attr="contains_raw_data_sources",
        indexed=False,
    )
    contains_information_requests = indexes.BooleanField(
        model_attr="contains_information_requests",
        indexed=False,
    )

    n_tables = indexes.IntegerField(
        model_attr="n_tables",
        indexed=False,
    )
    n_raw_data_sources = indexes.IntegerField(
        model_attr="n_raw_data_sources",
        indexed=False,
    )
    n_information_requests = indexes.IntegerField(
        model_attr="n_information_requests",
        indexed=False,
    )

    first_table_id = indexes.CharField(
        model_attr="first_table_id",
        default="",
        indexed=False,
    )
    first_open_table_id = indexes.CharField(
        model_attr="first_open_table_id",
        default="",
        indexed=False,
    )
    first_closed_table_id = indexes.CharField(
        model_attr="first_closed_table_id",
        default="",
        indexed=False,
    )
    first_raw_data_source_id = indexes.CharField(
        model_attr="first_raw_data_source_id",
        default="",
        indexed=False,
    )
    first_information_request_id = indexes.CharField(
        model_attr="first_information_request_id",
        default="",
        indexed=False,
    )

    def get_model(self):
        return Dataset

    def read_queryset(self, using=None):
        return self.get_model().objects.exclude(status__slug="under_review")

    def index_queryset(self, using=None):
        return self.get_model().objects.exclude(status__slug="under_review")

    def load_all_queryset(self, using=None):
        return self.get_model().objects.exclude(status__slug="under_review")

    def prepare_organization_picture(self, obj):
        return getattr(obj.organization.picture, "name", None)
