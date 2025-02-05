# -*- coding: utf-8 -*-
from haystack import indexes

from backend.apps.api.v1.models import Dataset


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
    dataset_name_pt = indexes.CharField(
        model_attr="name_pt",
        null=True,
        indexed=False,
    )
    dataset_name_en = indexes.CharField(
        model_attr="name_en",
        null=True,
        indexed=False,
    )
    dataset_name_es = indexes.CharField(
        model_attr="name_es",
        null=True,
        indexed=False,
    )
    dataset_description_pt = indexes.CharField(
        model_attr="description_pt",
        null=True,
        indexed=False,
    )
    dataset_description_en = indexes.CharField(
        model_attr="description_en",
        null=True,
        indexed=False,
    )
    dataset_description_es = indexes.CharField(
        model_attr="description_es",
        null=True,
        indexed=False,
    )

    spatial_coverage = indexes.MultiValueField(
        model_attr="spatial_coverage",
        null=True,
        faceted=True,
        indexed=True,
    )

    temporal_coverage = indexes.MultiValueField(
        model_attr="temporal_coverage",
        null=True,
        faceted=True,
        indexed=True,
    )

    table_id = indexes.MultiValueField(
        model_attr="tables__pk",
        indexed=False,
    )
    table_slug = indexes.MultiValueField(
        model_attr="tables__slug",
        indexed=False,
    )
    table_name_pt = indexes.MultiValueField(
        model_attr="tables__name_pt",
        null=True,
        indexed=False,
    )
    table_name_en = indexes.MultiValueField(
        model_attr="tables__name_en",
        null=True,
        indexed=False,
    )
    table_name_es = indexes.MultiValueField(
        model_attr="tables__name_es",
        null=True,
        indexed=False,
    )
    table_description_pt = indexes.MultiValueField(
        model_attr="tables__description_pt",
        null=True,
        indexed=False,
    )
    table_description_en = indexes.MultiValueField(
        model_attr="tables__description_en",
        null=True,
        indexed=False,
    )
    table_description_es = indexes.MultiValueField(
        model_attr="tables__description_es",
        null=True,
        indexed=False,
    )

    organization_id = indexes.MultiValueField(
        model_attr="organizations__id",
        faceted=True,
        indexed=False,
    )
    organization_slug = indexes.MultiValueField(
        model_attr="organizations__slug",
        faceted=True,
        indexed=False,
    )
    organization_name = indexes.MultiValueField(
        model_attr="organizations__name",
        faceted=True,
        indexed=False,
    )
    organization_name_pt = indexes.MultiValueField(
        model_attr="organizations__name_pt",
        null=True,
        faceted=True,
        indexed=False,
    )
    organization_name_en = indexes.MultiValueField(
        model_attr="organizations__name_en",
        null=True,
        faceted=True,
        indexed=False,
    )
    organization_name_es = indexes.MultiValueField(
        model_attr="organizations__name_es",
        null=True,
        faceted=True,
        indexed=False,
    )
    organization_picture = indexes.MultiValueField(
        model_attr="organizations__picture",
        default="",
        indexed=False,
    )
    organization_website = indexes.MultiValueField(
        model_attr="organizations__website",
        default="",
        indexed=False,
    )
    organization_description_pt = indexes.MultiValueField(
        model_attr="organizations__description_pt",
        null=True,
        indexed=False,
    )
    organization_description_en = indexes.MultiValueField(
        model_attr="organizations__description_en",
        null=True,
        indexed=False,
    )
    organization_description_es = indexes.MultiValueField(
        model_attr="organizations__description_es",
        null=True,
        indexed=False,
    )

    tag_slug = indexes.MultiValueField(
        model_attr="tags__slug",
        default="",
        faceted=True,
        indexed=False,
    )
    tag_name_pt = indexes.MultiValueField(
        model_attr="tags__name_pt",
        null=True,
        faceted=True,
        indexed=False,
    )
    tag_name_en = indexes.MultiValueField(
        model_attr="tags__name_en",
        null=True,
        faceted=True,
        indexed=False,
    )
    tag_name_es = indexes.MultiValueField(
        model_attr="tags__name_es",
        null=True,
        faceted=True,
        indexed=False,
    )
    theme_slug = indexes.MultiValueField(
        model_attr="themes__slug",
        default="",
        faceted=True,
        indexed=False,
    )
    theme_name_pt = indexes.MultiValueField(
        model_attr="themes__name_pt",
        null=True,
        faceted=True,
        indexed=False,
    )
    theme_name_en = indexes.MultiValueField(
        model_attr="themes__name_en",
        null=True,
        faceted=True,
        indexed=False,
    )
    theme_name_es = indexes.MultiValueField(
        model_attr="themes__name_es",
        null=True,
        faceted=True,
        indexed=False,
    )
    entity_slug = indexes.MultiValueField(
        model_attr="tables__observation_levels__entity__slug",
        default="",
        faceted=True,
        indexed=False,
    )
    entity_name_pt = indexes.MultiValueField(
        model_attr="tables__observation_levels__entity__name_pt",
        null=True,
        faceted=True,
        indexed=False,
    )
    entity_name_en = indexes.MultiValueField(
        model_attr="tables__observation_levels__entity__name_en",
        null=True,
        faceted=True,
        indexed=False,
    )
    entity_name_es = indexes.MultiValueField(
        model_attr="tables__observation_levels__entity__name_es",
        null=True,
        faceted=True,
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
        """
        Get pictures from all organizations associated with the dataset
        """
        pictures = []
        for org in obj.organizations.all():
            pictures.append(getattr(org.picture, "name", None))
        return pictures

    def get_field_mapping(self):
        mapping = super().get_field_mapping()
        mapping["spatial_coverage"] = {
            "type": "keyword",
            "store": True,
            "index": True,
        }
        return mapping

    def prepare(self, obj):
        data = super().prepare(obj)

        organization_fields = [
            "organization_id",
            "organization_slug",
            "organization_name",
            "organization_name_pt",
            "organization_name_en",
            "organization_name_es",
            "organization_picture",
            "organization_website",
            "organization_description_pt",
            "organization_description_en",
            "organization_description_es",
        ]

        for field in organization_fields:
            if field in data and not isinstance(data[field], (list, tuple)):
                data[field] = [data[field]] if data[field] is not None else []

        return data
