# -*- coding: utf-8 -*-
from django.core.files.storage import get_storage_class
from haystack import indexes
from .models import (
    Dataset,
)


class DatasetIndex(indexes.SearchIndex, indexes.Indexable):
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

    column_ids = indexes.MultiValueField(model_attr="tables__columns__id", null=True)
    column_names = indexes.MultiValueField(
        model_attr="tables__columns__name", null=True
    )
    column_descriptions = indexes.EdgeNgramField(
        model_attr="tables__columns__description", null=True
    )

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
    observation_levels = indexes.MultiValueField(
        model_attr="tables__observation_levels__entity__name", null=True
    )
    raw_data_sources = indexes.MultiValueField(
        model_attr="raw_data_sources__id", null=True
    )
    information_requests = indexes.MultiValueField(
        model_attr="information_requests__id", null=True
    )
    is_closed = indexes.BooleanField(model_attr="is_closed")
    contains_tables = indexes.BooleanField(model_attr="contains_tables")
    contains_raw_data_sources = indexes.BooleanField(
        model_attr="contains_raw_data_sources"
    )
    contains_information_requests = indexes.BooleanField(
        model_attr="contains_information_requests"
    )

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

        storage = get_storage_class()  # This will use DEFAULT_FILE_STORAGE
        if (
            obj.organization
            and obj.organization.picture
            and obj.organization.picture.name
        ):
            organization_picture = storage().url(obj.organization.picture.name)
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
                    }
                )
            data["total_tables"] = len(table_ids)
        else:
            data["total_tables"] = 0

        # columns
        column_ids = data.get("column_ids", [])
        if column_ids:
            data["columns"] = []
            for i in range(len(column_ids)):
                data["columns"].append(
                    {
                        "id": data.get("column_ids", [])[i],
                        "name": data.get("column_names", [])[i],
                        "description": data.get("column_descriptions", [])[i],
                    }
                )

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

        # Is closed
        is_closed = data.get("is_closed", False)
        data["is_closed"] = is_closed

        # Coverage
        coverage = data.get("coverage", "")
        if coverage == " - ":
            data["coverage"] = ""

        # Observation Levels
        observation_levels = data.get("observations", [])
        data["observations"] = observation_levels if observation_levels else ""

        # Contains tables
        contains_tables = data.get("contains_tables", False)
        data["contains_tables"] = contains_tables

        # Contains raw data sources
        contains_raw_data_sources = data.get("contains_raw_data_sources", False)
        data["contains_raw_data_sources"] = contains_raw_data_sources

        # Contains information requests
        contains_information_requests = data.get("contains_information_requests", False)
        data["contains_information_requests"] = contains_information_requests

        return data
