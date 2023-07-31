# -*- coding: utf-8 -*-
from haystack import indexes
from .models import (
    Dataset,
)


class DatasetIndex(indexes.SearchIndex, indexes.Indexable):
    updated_at = indexes.DateTimeField(model_attr="updated_at")
    text = indexes.CharField(document=True, use_template=True)
    slug = indexes.CharField(model_attr="slug")
    name = indexes.CharField(model_attr="name")
    description = indexes.EdgeNgramField(model_attr="description", null=True)

    organization_id = indexes.CharField(model_attr="organization__id", null=True)
    organization_slug = indexes.CharField(model_attr="organization__slug")
    organization_name = indexes.CharField(model_attr="organization__name")
    organization_description = indexes.CharField(
        model_attr="organization__description", null=True
    )
    organization_picture = indexes.CharField(
        model_attr="organization__picture", null=True
    )
    organization_website = indexes.CharField(
        model_attr="organization__website", null=True
    )

    table_ids = indexes.MultiValueField(model_attr="tables__id", null=True)
    table_slugs = indexes.MultiValueField(model_attr="tables__slug", null=True)
    table_names = indexes.MultiValueField(model_attr="tables__name", null=True)
    table_descriptions = indexes.EdgeNgramField(
        model_attr="tables__description", null=True
    )
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
    raw_data_sources = indexes.MultiValueField(
        model_attr="raw_data_sources__id", null=True
    )
    information_requests = indexes.MultiValueField(
        model_attr="information_requests__id", null=True
    )
    is_closed = indexes.BooleanField(model_attr="is_closed")
    contains_tables = indexes.BooleanField(model_attr="contains_tables")
    contains_closed_data = indexes.BooleanField(model_attr="contains_closed_data")
    contains_open_tables = indexes.BooleanField(model_attr="contains_open_tables")
    contains_closed_tables = indexes.BooleanField(model_attr="contains_closed_tables")
    contains_raw_data_sources = indexes.BooleanField(
        model_attr="contains_raw_data_sources"
    )
    contains_information_requests = indexes.BooleanField(
        model_attr="contains_information_requests"
    )

    status_slug = indexes.MultiValueField(model_attr="status__slug", null=True)

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
            closed_tables = obj.tables.filter(is_closed=True)
            data["n_closed_tables"] = closed_tables.count()
            data["n_tables"] = len(table_ids)

        # organization
        organization_id = data.get("organization_id", "")
        organization_name = data.get("organization_name", "")
        organization_slug = data.get("organization_slug", "")

        if (
            obj.organization
            and obj.organization.picture
            and obj.organization.picture.name
        ):
            organization_picture = obj.organization.picture.name
        else:
            organization_picture = ""

        organization_website = data.get("organization_website", "")
        organization_description = data.get("organization_description", "")
        data["organization"] = {
            "id": organization_id,
            "name": organization_name,
            "slug": organization_slug,
            "picture": organization_picture,
            "website": organization_website,
            "description": organization_description,
        }

        # themes
        themes_slug = data.get("themes_slug", [])
        if themes_slug:
            data["themes"] = []
            for i in range(len(themes_slug)):
                data["themes"].append(
                    {
                        "name": data.get("themes_name", [])[i],
                        "keyword": data.get("themes_keyword", [])[i],
                    }
                )

        # tags
        tags_slug = data.get("tags_slug", [])
        if tags_slug:
            data["tags"] = []
            for i in range(len(tags_slug)):
                data["tags"].append(
                    {
                        "name": data.get("tags_name", [])[i],
                        "keyword": data.get("tags_keyword", [])[i],
                    }
                )

        # tables
        table_ids = data.get("table_slugs", [])
        if table_ids:
            data["tables"] = []
            for i in range(len(table_ids)):
                data["tables"].append(
                    {
                        "id": data.get("table_ids", [])[i],
                        "name": data.get("table_names", [])[i],
                        "slug": data.get("table_slugs", [])[i],
                        "is_closed": data.get("table_is_closed", [])[i],
                    }
                )
            data["total_tables"] = len(table_ids)
        else:
            data["total_tables"] = 0

        # Raw data sources
        raw_data_sources = data.get("raw_data_sources", [])
        data["first_raw_data_source_id"] = (
            raw_data_sources[0] if raw_data_sources else ""
        )
        if raw_data_sources:
            data["n_raw_data_sources"] = len(raw_data_sources)
        else:
            data["n_raw_data_sources"] = 0

        # Information requests
        information_requests = data.get("information_requests", [])
        data["first_information_request_id"] = (
            information_requests[0] if information_requests else ""
        )
        if information_requests:
            data["n_information_requests"] = len(information_requests)
        else:
            data["n_information_requests"] = 0

        # Status
        status = data.get("status__slug", "")
        data["status"] = status

        # Is closed
        is_closed = data.get("is_closed", False)
        data["is_closed"] = is_closed

        # Coverage
        coverage = data.get("coverage", "")
        if coverage == " - ":
            data["coverage"] = ""

        # Observation Levels
        observation_levels = data.get("observation_levels_name", [])
        if observation_levels:
            data["observation_levels"] = []
            for i in range(len(observation_levels)):
                data["observation_levels"].append(
                    {
                        "name": data.get("observation_levels_name", [])[i],
                        "keyword": data.get("observation_levels_keyword", [])[i],
                    }
                )

        # Contains tables
        contains_tables = data.get("contains_tables", False)
        data["contains_tables"] = contains_tables

        # Contains closed data
        contains_closed_data = data.get("contains_closed_data", False)
        data["contains_closed_data"] = contains_closed_data

        # Contains open tables
        contains_open_tables = data.get("contains_open_tables", False)
        data["contains_open_tables"] = contains_open_tables

        # Contains closed tables
        contains_closed_tables = data.get("contains_closed_tables", False)
        data["contains_closed_tables"] = contains_closed_tables

        # Contains raw data sources
        contains_raw_data_sources = data.get("contains_raw_data_sources", False)
        data["contains_raw_data_sources"] = contains_raw_data_sources

        # Contains information requests
        contains_information_requests = data.get("contains_information_requests", False)
        data["contains_information_requests"] = contains_information_requests

        return data
