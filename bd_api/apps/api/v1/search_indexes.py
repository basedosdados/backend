# -*- coding: utf-8 -*-
from haystack import indexes

from .models import Dataset


def list2dict(data, keys: list[str]):
    """Turn multiple lists into a list of dicts

    ```
    keys = ["name", "age"]
    data = {"name": ["jose", "maria"], "age": [18, 27]}
    dict = [{"name": "jose", "age": 18}, {"name": "maria", "age": 27}]
    ```
    """
    multivalues = zip(data.get(key, []) for key in keys)
    return [dict(zip(keys, values)) for values in multivalues]


class DatasetIndex(indexes.SearchIndex, indexes.Indexable):
    updated_at = indexes.DateTimeField(model_attr="updated_at")

    text = indexes.CharField(document=True, use_template=True)
    slug = indexes.CharField(model_attr="slug")
    name = indexes.EdgeNgramField(model_attr="name")
    description = indexes.EdgeNgramField(model_attr="description", null=True)

    organization_id = indexes.CharField(model_attr="organization__id", null=True)
    organization_slug = indexes.CharField(model_attr="organization__slug")
    organization_name = indexes.EdgeNgramField(model_attr="organization__name")
    organization_description = indexes.CharField(model_attr="organization__description", null=True)
    organization_picture = indexes.CharField(model_attr="organization__picture", null=True)
    organization_website = indexes.CharField(model_attr="organization__website", null=True)

    table_ids = indexes.MultiValueField(model_attr="tables__id", null=True)
    table_slugs = indexes.MultiValueField(model_attr="tables__slug", null=True)
    table_names = indexes.EdgeNgramField(model_attr="tables__name", null=True)
    table_descriptions = indexes.EdgeNgramField(model_attr="tables__description", null=True)
    table_is_closed = indexes.MultiValueField(model_attr="tables__is_closed", null=True)

    themes_name = indexes.MultiValueField(model_attr="themes__name", null=True)
    themes_slug = indexes.MultiValueField(model_attr="themes__slug", null=True)
    themes_keyword = indexes.MultiValueField(
        model_attr="themes__slug", null=True, indexed=True, stored=True
    )

    tags_name = indexes.MultiValueField(model_attr="tags__name", null=True)
    tags_slug = indexes.MultiValueField(model_attr="tags__slug", null=True)
    tags_keyword = indexes.MultiValueField(
        model_attr="tags__slug", null=True, indexed=True, stored=True
    )

    coverage = indexes.MultiValueField(model_attr="coverage", null=True)
    observation_levels_name = indexes.MultiValueField(
        model_attr="tables__observation_levels__entity__name", null=True
    )
    observation_levels_keyword = indexes.MultiValueField(
        model_attr="tables__observation_levels__entity__slug", null=True
    )
    raw_data_sources = indexes.MultiValueField(model_attr="raw_data_sources__id", null=True)
    information_requests = indexes.MultiValueField(model_attr="information_requests__id", null=True)
    is_closed = indexes.BooleanField(model_attr="is_closed")
    contains_tables = indexes.BooleanField(model_attr="contains_tables")
    contains_closed_data = indexes.BooleanField(model_attr="contains_closed_data")
    contains_open_data = indexes.BooleanField(model_attr="contains_open_data")
    contains_raw_data_sources = indexes.BooleanField(model_attr="contains_raw_data_sources")
    contains_information_requests = indexes.BooleanField(model_attr="contains_information_requests")

    status_slug = indexes.MultiValueField(model_attr="status__slug", null=True)

    def get_model(self):
        return Dataset

    def index_queryset(self, using=None):
        return self.get_model().objects.all()

    def prepare(self, obj):
        data = super().prepare(obj)
        data = self._prepare_tags(obj, data)
        data = self._prepare_table(obj, data)
        data = self._prepare_theme(obj, data)
        data = self._prepare_coverage(obj, data)
        data = self._prepare_metadata(obj, data)
        data = self._prepare_organization(obj, data)
        data = self._prepare_raw_data_source(obj, data)
        data = self._prepare_observation_level(obj, data)
        data = self._prepare_information_request(obj, data)
        return data

    def _prepare_tags(self, obj, data):
        if tags := data.get("tags_slug", []):
            data["tags"] = []
            for i, _ in enumerate(tags):
                data["tags"].append(
                    {
                        "name": data["tags_name"][i],
                        "keyword": data["tags_keyword"][i],
                    }
                )
        return data

    def _prepare_table(self, obj, data):
        if table_ids := data.get("table_ids", []):
            published_tables = obj.tables.exclude(status__slug__in=["under_review"])
            data["n_tables"] = published_tables.count()
            data["first_table_id"] = table_ids[0]
            if published_tables.first():
                data["first_table_id"] = published_tables.first().id

            data["tables"] = []
            for i, _ in enumerate(table_ids):
                data["tables"].append(
                    {
                        "id": data["table_ids"][i],
                        "name": data["table_names"][i],
                        "slug": data["table_slugs"][i],
                        "is_closed": data["table_is_closed"][i],
                    }
                )
            data["total_tables"] = len(table_ids)
        else:
            data["n_tables"] = 0
            data["total_tables"] = 0
        return data

    def _prepare_theme(self, obj, data):
        if themes_slug := data.get("themes_slug", []):
            data["themes"] = []
            for i, _ in enumerate(themes_slug):
                data["themes"].append(
                    {
                        "name": data["themes_name"][i],
                        "keyword": data["themes_keyword"][i],
                    }
                )
        return data

    def _prepare_coverage(self, obj, data):
        coverage = data.get("coverage", "")
        if coverage == " - ":
            data["coverage"] = ""
        return data

    def _prepare_metadata(self, obj, data):
        data["status"] = data.get("status__slug", "")
        data["is_closed"] = data.get("is_closed", False)
        data["contains_tables"] = data.get("contains_tables", False)
        data["contains_open_data"] = data.get("contains_open_data", False)
        data["contains_closed_data"] = data.get("contains_closed_data", False)
        data["contains_raw_data_sources"] = data.get("contains_raw_data_sources", False)
        data["contains_information_requests"] = data.get("contains_information_requests", False)
        return data

    def _prepare_organization(self, obj, data):
        organization_picture = ""
        if obj.organization and obj.organization.picture and obj.organization.picture.name:
            organization_picture = obj.organization.picture.name
        data["organization"] = {
            "id": data.get("organization_id", ""),
            "name": data.get("organization_name", ""),
            "slug": data.get("organization_slug", ""),
            "picture": organization_picture,
            "website": data.get("organization_website", ""),
            "description": data.get("organization_description", ""),
        }
        return data

    def _prepare_raw_data_source(self, obj, data):
        if raw_data_sources := data.get("raw_data_sources", []):
            data["n_raw_data_sources"] = len(raw_data_sources)
            data["first_raw_data_source_id"] = raw_data_sources[0]
        else:
            data["n_raw_data_sources"] = 0
            data["first_raw_data_source_id"] = ""
        return data

    def _prepare_observation_level(self, obj, data):
        if observation_levels_name := data.get("observation_levels_name", []):
            data["observation_levels"] = []
            for i, _ in enumerate(observation_levels_name):
                data["observation_levels"].append(
                    {
                        "name": data["observation_levels_name"][i],
                        "keyword": data["observation_levels_keyword"][i],
                    }
                )
        return data

    def _prepare_information_request(self, obj, data):
        if information_requests := data.get("information_requests", []):
            data["n_information_requests"] = len(information_requests)
            data["first_information_request_id"] = information_requests[0]
        else:
            data["n_information_requests"] = 0
            data["first_information_request_id"] = ""
        return data
