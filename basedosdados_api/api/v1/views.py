# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from typing import Dict, List, Tuple, Union

from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, QueryDict, JsonResponse
from haystack.forms import ModelSearchForm
from haystack.generic_views import SearchView

from elasticsearch import Elasticsearch

from basedosdados_api.api.v1.models import Coverage, Dataset


class DatasetSearchView(SearchView):
    def get(self, request, *args, **kwargs):
        """
        Handles GET requests and instantiates a blank version of the form.
        """
        # Get request arguments
        req_args: QueryDict = request.GET.copy()
        query = req_args.get("q", None)

        # If query is empty, build dataset_list with all datasets
        if not query:
            dataset_list: List[Dataset] = list(Dataset.objects.all())

        # If query is not empty, search for datasets
        else:
            form_class = self.get_form_class()
            form: ModelSearchForm = self.get_form(form_class)
            if not form.is_valid():
                return HttpResponseBadRequest(json.dumps({"error": "Invalid form"}))
            self.queryset = form.search()
            context = self.get_context_data(
                **{
                    self.form_name: form,
                    "query": form.cleaned_data.get(self.search_field),
                    "object_list": self.queryset,
                }
            )
            # Raw dataset list
            dataset_list: List[Dataset] = [obj.object for obj in context["object_list"]]

        # Try to get filter method from request arguments
        filter_method = req_args.get("filter_method", "and")
        if filter_method not in ["and", "or"]:
            return HttpResponseBadRequest(
                json.dumps({"error": "Invalid filter method"})
            )

        # Filtering
        if "is_closed" in req_args:
            # Filter by is_closed
            is_closed = req_args.get("is_closed")
            if is_closed == "true":
                dataset_list = [ds for ds in dataset_list if ds.is_closed]
            elif is_closed == "false":
                dataset_list = [ds for ds in dataset_list if not ds.is_closed]
            else:
                return HttpResponseBadRequest(
                    json.dumps({"error": "Invalid value for 'is_closed'"})
                )

        if "theme" in req_args:
            # Filter by theme slugs
            theme_slugs = req_args.getlist("theme")
            new_dataset_list = []
            if filter_method == "or":
                for dataset in dataset_list:
                    for theme in dataset.themes.all():
                        if theme.slug in theme_slugs:
                            new_dataset_list.append(dataset)
                            break
            elif filter_method == "and":
                for dataset in dataset_list:
                    themes = [theme.slug for theme in dataset.themes.all()]
                    if all([theme in themes for theme in theme_slugs]):
                        new_dataset_list.append(dataset)
            dataset_list = new_dataset_list
        if "organization" in req_args:
            # Filter by organization slugs
            organization_slugs = req_args.getlist("organization")
            if filter_method == "or":
                dataset_list = [
                    ds
                    for ds in dataset_list
                    if ds.organization.slug in organization_slugs
                ]
            elif filter_method == "and":
                return HttpResponseBadRequest(
                    json.dumps(
                        {
                            "error": "Invalid filter method: 'and' not supported for 'organization'"
                        }
                    )
                )
        if "tag" in req_args:
            # Filter by tag slugs
            tag_slugs = req_args.getlist("tag")
            new_dataset_list = []
            if filter_method == "or":
                for dataset in dataset_list:
                    for tag in dataset.tags.all():
                        if tag.slug in tag_slugs:
                            new_dataset_list.append(dataset)
                            break
            elif filter_method == "and":
                for dataset in dataset_list:
                    tags = [tag.slug for tag in dataset.tags.all()]
                    if all([tag in tags for tag in tag_slugs]):
                        new_dataset_list.append(dataset)
            dataset_list = new_dataset_list
        if "spatial_coverage" in req_args or "temporal_coverage" in req_args:
            # Collect all coverage objects
            coverages: Dict[str, List[Coverage]] = {}
            added_coverages = set()
            for dataset in dataset_list:
                for table in dataset.tables.all():
                    for coverage in table.coverages.all():
                        if coverage.id not in added_coverages:
                            if dataset.slug not in coverages:
                                coverages[dataset.slug] = []
                            coverages[dataset.slug].append(coverage)
                            added_coverages.add(coverage.id)
                for raw_data_source in dataset.raw_data_sources.all():
                    for coverage in raw_data_source.coverages.all():
                        if coverage.id not in added_coverages:
                            if dataset.slug not in coverages:
                                coverages[dataset.slug] = []
                            coverages[dataset.slug].append(coverage)
                            added_coverages.add(coverage.id)
                for information_request in dataset.information_requests.all():
                    for coverage in information_request.coverages.all():
                        if coverage.id not in added_coverages:
                            if dataset.slug not in coverages:
                                coverages[dataset.slug] = []
                            coverages[dataset.slug].append(coverage)
                            added_coverages.add(coverage.id)
        if "spatial_coverage" in req_args:
            # Filter by spatial coverages
            spatial_coverages = req_args.getlist("spatial_coverage")
            new_dataset_list = []
            added_datasets = set()
            if filter_method == "or":
                for dataset in dataset_list:
                    if dataset.slug in coverages:
                        for coverage in coverages[dataset.slug]:
                            for spatial_coverage in spatial_coverages:
                                if coverage.area.slug.startswith(spatial_coverage):
                                    new_dataset_list.append(dataset)
                                    added_datasets.add(dataset.slug)
                                    break
                            if dataset.slug in added_datasets:
                                break
            elif filter_method == "and":
                for dataset in dataset_list:
                    if dataset.slug in coverages:
                        spatial_coverages_found = 0
                        for coverage in coverages[dataset.slug]:
                            for spatial_coverage in spatial_coverages:
                                if coverage.area.slug.startswith(spatial_coverage):
                                    spatial_coverages_found += 1
                                    break
                            if spatial_coverages_found == len(spatial_coverages):
                                new_dataset_list.append(dataset)
                                break
            dataset_list = new_dataset_list
        if "temporal_coverage" in req_args:
            # Filter by temporal coverage
            temporal_coverage = req_args["temporal_coverage"]
            start_year, end_year = temporal_coverage.split("-")
            start_year = int(start_year)
            end_year = int(end_year)
            new_dataset_list = []
            added_datasets = set()
            for dataset in dataset_list:
                if dataset.slug in coverages:
                    for coverage in coverages[dataset.slug]:
                        for datetime_range in coverage.datetime_ranges.all():
                            if (
                                datetime_range.start_year <= start_year
                                and datetime_range.end_year >= end_year
                            ):
                                new_dataset_list.append(dataset)
                                added_datasets.add(dataset.slug)
                                break
                        if dataset.slug in added_datasets:
                            break
            dataset_list = new_dataset_list
        if "entity" in req_args:
            # Collect all entities
            entities: Dict[str, List[str]] = {}
            added_entities = set()
            for dataset in dataset_list:
                for table in dataset.tables.all():
                    for observation_level in table.observation_levels.all():
                        entity = observation_level.entity
                        if entity.id not in added_entities:
                            if dataset.slug not in entities:
                                entities[dataset.slug] = []
                            entities[dataset.slug].append(entity.slug)
                            added_entities.add(entity.id)
                for raw_data_source in dataset.raw_data_sources.all():
                    for observation_level in raw_data_source.observation_levels.all():
                        entity = observation_level.entity
                        if entity.id not in added_entities:
                            if dataset.slug not in entities:
                                entities[dataset.slug] = []
                            entities[dataset.slug].append(entity.slug)
                            added_entities.add(entity.id)
                for information_request in dataset.information_requests.all():
                    for (
                        observation_level
                    ) in information_request.observation_levels.all():
                        entity = observation_level.entity
                        if entity.id not in added_entities:
                            if dataset.slug not in entities:
                                entities[dataset.slug] = []
                            entities[dataset.slug].append(entity.slug)
                            added_entities.add(entity.id)
            # Filter by entity slugs
            entity_slugs = req_args.getlist("entity")
            new_dataset_list = []
            if filter_method == "or":
                for dataset in dataset_list:
                    for entity_slug in entity_slugs:
                        if (
                            dataset.slug in entities
                            and entity_slug in entities[dataset.slug]
                        ):
                            new_dataset_list.append(dataset)
                            break
            elif filter_method == "and":
                for dataset in dataset_list:
                    entities_found = 0
                    for entity_slug in entity_slugs:
                        if (
                            dataset.slug in entities
                            and entity_slug in entities[dataset.slug]
                        ):
                            entities_found += 1
                    if entities_found == len(entity_slugs):
                        new_dataset_list.append(dataset)
            dataset_list = new_dataset_list
        if "update_frequency" in req_args:
            update_frequencies: List[Tuple[int, str]] = [
                self.split_number_text(frequency)
                for frequency in req_args.getlist("update_frequency")
            ]
            # Collect all updates
            updates: Dict[str, List[Tuple[int, str]]] = {}
            added_updates = set()
            for dataset in dataset_list:
                for table in dataset.tables.all():
                    for update in table.updates.all():
                        if update.id not in added_updates:
                            if dataset.slug not in updates:
                                updates[dataset.slug] = []
                            updates[dataset.slug].append(
                                (update.frequency, update.entity.slug)
                            )
                            added_updates.add(update.id)
                for raw_data_source in dataset.raw_data_sources.all():
                    for update in raw_data_source.updates.all():
                        if update.id not in added_updates:
                            if dataset.slug not in updates:
                                updates[dataset.slug] = []
                            updates[dataset.slug].append(
                                (update.frequency, update.entity.slug)
                            )
                            added_updates.add(update.id)
                for information_request in dataset.information_requests.all():
                    for update in information_request.updates.all():
                        if update.id not in added_updates:
                            if dataset.slug not in updates:
                                updates[dataset.slug] = []
                            updates[dataset.slug].append(
                                (update.frequency, update.entity.slug)
                            )
                            added_updates.add(update.id)
            # Filter by update frequencies
            new_dataset_list = []
            if filter_method == "or":
                for dataset in dataset_list:
                    for update_frequency in update_frequencies:
                        if (
                            dataset.slug in updates
                            and update_frequency in updates[dataset.slug]
                        ):
                            new_dataset_list.append(dataset)
                            break
            elif filter_method == "and":
                return HttpResponseBadRequest(
                    json.dumps(
                        {
                            "error": "Invalid filter method: 'and' not supported for 'update_frequency'"
                        }
                    )
                )
            dataset_list = new_dataset_list
        if "raw_quality_tier" in req_args:
            # TODO: filter by raw quality tier
            ...
        # Pagination
        try:
            if "page_size" in req_args:
                page_size = int(req_args["page_size"])
            else:
                page_size = 10
            if page_size < 1:
                raise ValueError("page_size must be greater than 0")
        except:  # noqa
            return HttpResponseBadRequest(json.dumps({"error": "Invalid page_size"}))
        try:
            if "page" in req_args:
                page = int(req_args["page"])
            else:
                page = 1
            if page < 1:
                raise ValueError("page must be greater than 0")
        except:  # noqa
            return HttpResponseBadRequest(json.dumps({"error": "Invalid page"}))
        page_dataset_list = dataset_list[
            (page - 1) * page_size : page * page_size  # noqa
        ]
        results = [self.serialize_dataset(ds) for ds in page_dataset_list]
        return HttpResponse(
            json.dumps(
                {
                    "count": len(dataset_list),
                    "results": results,
                }
            ),
            status=200 if len(results) > 0 else 204,
        )

    def serialize_dataset(self, dataset: Dataset):
        def get_temporal_coverage(dataset: Dataset) -> str:
            min_year = float("inf")
            max_year = float("-inf")
            datetimes = []
            added_datetime_ids = set()
            added_coverages = set()
            for table in dataset.tables.all():
                for coverage in table.coverages.all():
                    if coverage.id not in added_coverages:
                        for datetime_range in coverage.datetime_ranges.all():
                            if datetime_range.id not in added_datetime_ids:
                                datetimes.append(datetime_range)
                                added_datetime_ids.add(datetime_range.id)
            for raw_data_source in dataset.raw_data_sources.all():
                for coverage in raw_data_source.coverages.all():
                    if coverage.id not in added_coverages:
                        for datetime_range in coverage.datetime_ranges.all():
                            if datetime_range.id not in added_datetime_ids:
                                datetimes.append(datetime_range)
                                added_datetime_ids.add(datetime_range.id)
            for information_request in dataset.information_requests.all():
                for coverage in information_request.coverages.all():
                    if coverage.id not in added_coverages:
                        for datetime_range in coverage.datetime_ranges.all():
                            if datetime_range.id not in added_datetime_ids:
                                datetimes.append(datetime_range)
                                added_datetime_ids.add(datetime_range.id)
            for datetime_range in datetimes:
                min_year = min(min_year, datetime_range.start_year)
                max_year = max(max_year, datetime_range.end_year)

            if min_year == max_year:
                return f"{min_year}"
            return f"{min_year}-{max_year}"

        def get_themes(dataset: Dataset) -> List[Dict[str, str]]:
            themes = []
            for theme in dataset.themes.all():
                themes.append(
                    {
                        "name": theme.name,
                        "slug": theme.slug,
                    }
                )
            return themes

        def get_tags(dataset: Dataset) -> List[Dict[str, str]]:
            tags = []
            for tag in dataset.tags.all():
                tags.append(
                    {
                        "name": tag.name,
                        "slug": tag.slug,
                    }
                )
            return tags

        def get_first_table_id(dataset: Dataset) -> Union[str, None]:
            if dataset.tables.count() > 0:
                return str(dataset.tables.first().id)
            return None

        def get_first_original_source_id(dataset: Dataset) -> Union[str, None]:
            if dataset.raw_data_sources.count() > 0:
                return str(dataset.raw_data_sources.first().id)
            return None

        def get_first_lai_id(dataset: Dataset) -> Union[str, None]:
            if dataset.information_requests.count() > 0:
                return str(dataset.information_requests.first().id)
            return None

        organization_picture = dataset.organization.picture
        if organization_picture:
            organization_picture = organization_picture.url
        else:
            organization_picture = None

        return {
            "id": str(dataset.id),
            "slug": dataset.slug,
            "full_slug": dataset.full_slug,
            "name": dataset.name,
            "organization": dataset.organization.name,
            "organization_slug": dataset.organization.slug,
            "organization_picture": organization_picture,
            "organization_website": dataset.organization.website,
            "themes": get_themes(dataset),
            "tags": get_tags(dataset),
            "temporal_coverage": get_temporal_coverage(dataset),
            "n_bdm_tables": dataset.tables.count(),
            "first_table_id": get_first_table_id(dataset),
            "n_original_sources": dataset.raw_data_sources.count(),
            "first_original_source_id": get_first_original_source_id(dataset),
            "n_lais": dataset.information_requests.count(),
            "first_lai_id": get_first_lai_id(dataset),
            "is_closed": dataset.is_closed,
        }

    def get_context_data(self, **kwargs):
        kwargs.setdefault("view", self)
        if self.extra_context is not None:
            kwargs.update(self.extra_context)
        return kwargs

    def split_number_text(self, text: str) -> Tuple[int, str]:
        """
        Splits a string into a number and text part. Examples:
        >>> split_number_text("1year")
        (1, 'year')
        >>> split_number_text("2 month")
        (2, 'month')
        >>> split_number_text("3minute")
        (3, 'minute')
        """
        number = ""
        for c in text:
            if c.isdigit():
                number += c
            else:
                break
        if number == "":
            return None, text
        return int(number), (text[len(number) :]).strip()  # noqa


class DatasetESSearchView(SearchView):
    def get(self, request, *args, **kwargs):
        """
        Handles GET requests and instantiates a blank version of the form.
        """
        # Get request arguments
        req_args: QueryDict = request.GET.copy()
        query = req_args.get("q", None)
        es = Elasticsearch(settings.HAYSTACK_CONNECTIONS["default"]["URL"])
        page_size = 10
        page = int(req_args.get("page", 1))

        # If query is empty, query all datasets
        if not query:
            raw_query = {
                "from": (page - 1) * page_size,
                "size": page_size,
                "query": {
                    "function_score": {
                        "query": {"match_all": {}},
                        "field_value_factor": {
                            "field": "n_bdm_tables",
                            "modifier": "square",
                            "factor": 2,
                            "missing": 0,
                        },
                        "boost_mode": "sum",
                    }
                },
                "sort": [{"_score": {"order": "desc"}}],
            }
        # If query is not empty, search for datasets
        else:
            raw_query = {
                "from": (page - 1) * page_size,
                "size": page_size,
                "query": {
                    "function_score": {
                        "query": {
                            "bool": {
                                "should": [
                                    {
                                        "match": {
                                            "description.exact": {
                                                "query": query,
                                                "boost": 10,
                                            }
                                        }
                                    },
                                    {"match": {"name": query}},
                                ]
                            }
                        },
                        "field_value_factor": {
                            "field": "n_bdm_tables",
                            "modifier": "square",
                            "factor": 2,
                            "missing": 0,
                        },
                        "boost_mode": "sum",
                    }
                },
                "sort": [{"_score": {"order": "desc"}}],
            }

        form_class = self.get_form_class()
        form: ModelSearchForm = self.get_form(form_class)
        if not form.is_valid():
            return HttpResponseBadRequest(json.dumps({"error": "Invalid form"}))
        self.queryset = es.search(
            index=settings.HAYSTACK_CONNECTIONS["default"]["INDEX_NAME"], body=raw_query
        )
        context = self.get_context_data(
            **{
                self.form_name: form,
                "query": form.cleaned_data.get(self.search_field),
                "object_list": self.queryset,
            }
        )

        # Get total number of results
        count = context["object_list"].get("hits").get("total").get("value")

        # Get results from elasticsearch
        es_results = context["object_list"].get("hits").get("hits")

        # Clean results
        res = []
        for idx, r in enumerate(es_results):
            r_dict = r.get("_source")
            r_dict["themes"] = []
            if r_dict.get("organization_picture"):
                r_dict["organization_picture"] = "/media/" + r_dict.get(
                    "organization_picture"
                )
            if r_dict.get("themes_name"):
                for idx, name in enumerate(r_dict.get("themes_name")):
                    d = {"name": name, "slug": r_dict.get("themes_slug")[idx]}
                    r_dict["themes"].append(d)
            r_dict["tags"] = []
            if r_dict.get("tags_name"):
                for idx, name in enumerate(r_dict.get("tags_name")):
                    d = {"name": name, "slug": r_dict.get("tags_slug")[idx]}
                    r_dict["tags"].append(d)
            r_dict["n_bdm_tables"] = r_dict.get("n_bdm_tables", 0)
            coverage = r_dict.get("coverage")[0]
            if coverage:
                if coverage == " - ":
                    coverage = ""
                if "inf" in coverage:
                    coverage = coverage.replace("inf", "")
            r_dict["temporal_coverage"] = coverage
            del r_dict["coverage"]
            res.append(r_dict)

        results = {"count": count, "results": res}
        max_score = context["object_list"].get("hits").get("max_score")  # noqa

        return JsonResponse(
            results,
            status=200 if len(results) > 0 else 204,
        )

    def filtered_results(
        self, dataset_list: List, req_args: QueryDict
    ) -> List | HttpResponse:
        # Try to get filter method from request arguments
        filter_method = req_args.get("filter_method", "and")
        if filter_method not in ["and", "or"]:
            return HttpResponseBadRequest(
                json.dumps({"error": "Invalid filter method"})
            )

        if "is_closed" in req_args:
            # Filter by is_closed
            is_closed = req_args.get("is_closed")
            if is_closed == "true":
                dataset_list = [ds for ds in dataset_list if ds.is_closed]
            elif is_closed == "false":
                dataset_list = [ds for ds in dataset_list if not ds.is_closed]
            else:
                return HttpResponseBadRequest(
                    json.dumps({"error": "Invalid value for 'is_closed'"})
                )
        if "theme" in req_args:
            # Filter by theme slugs
            theme_slugs = req_args.getlist("theme")
            new_dataset_list = []
            if filter_method == "or":
                for dataset in dataset_list:
                    for theme in dataset.themes.all():
                        if theme.slug in theme_slugs:
                            new_dataset_list.append(dataset)
                            break
            elif filter_method == "and":
                for dataset in dataset_list:
                    themes = [theme.slug for theme in dataset.themes.all()]
                    if all([theme in themes for theme in theme_slugs]):
                        new_dataset_list.append(dataset)
            dataset_list = new_dataset_list
        if "organization" in req_args:
            # Filter by organization slugs
            organization_slugs = req_args.getlist("organization")
            if filter_method == "or":
                dataset_list = [
                    ds
                    for ds in dataset_list
                    if ds.organization.slug in organization_slugs
                ]
            elif filter_method == "and":
                return HttpResponseBadRequest(
                    json.dumps(
                        {
                            "error": "Invalid filter method: 'and' not supported for 'organization'"
                        }
                    )
                )
        if "tag" in req_args:
            # Filter by tag slugs
            tag_slugs = req_args.getlist("tag")
            new_dataset_list = []
            if filter_method == "or":
                for dataset in dataset_list:
                    for tag in dataset.tags.all():
                        if tag.slug in tag_slugs:
                            new_dataset_list.append(dataset)
                            break
            elif filter_method == "and":
                for dataset in dataset_list:
                    tags = [tag.slug for tag in dataset.tags.all()]
                    if all([tag in tags for tag in tag_slugs]):
                        new_dataset_list.append(dataset)
            dataset_list = new_dataset_list
        if "spatial_coverage" in req_args or "temporal_coverage" in req_args:
            # Collect all coverage objects
            coverages: Dict[str, List[Coverage]] = {}
            added_coverages = set()
            for dataset in dataset_list:
                for table in dataset.tables.all():
                    for coverage in table.coverages.all():
                        if coverage.id not in added_coverages:
                            if dataset.slug not in coverages:
                                coverages[dataset.slug] = []
                            coverages[dataset.slug].append(coverage)
                            added_coverages.add(coverage.id)
                for raw_data_source in dataset.raw_data_sources.all():
                    for coverage in raw_data_source.coverages.all():
                        if coverage.id not in added_coverages:
                            if dataset.slug not in coverages:
                                coverages[dataset.slug] = []
                            coverages[dataset.slug].append(coverage)
                            added_coverages.add(coverage.id)
                for information_request in dataset.information_requests.all():
                    for coverage in information_request.coverages.all():
                        if coverage.id not in added_coverages:
                            if dataset.slug not in coverages:
                                coverages[dataset.slug] = []
                            coverages[dataset.slug].append(coverage)
                            added_coverages.add(coverage.id)
        if "spatial_coverage" in req_args:
            # Filter by spatial coverages
            spatial_coverages = req_args.getlist("spatial_coverage")
            new_dataset_list = []
            added_datasets = set()
            if filter_method == "or":
                for dataset in dataset_list:
                    if dataset.slug in coverages:
                        for coverage in coverages[dataset.slug]:
                            for spatial_coverage in spatial_coverages:
                                if coverage.area.slug.startswith(spatial_coverage):
                                    new_dataset_list.append(dataset)
                                    added_datasets.add(dataset.slug)
                                    break
                            if dataset.slug in added_datasets:
                                break
            elif filter_method == "and":
                for dataset in dataset_list:
                    if dataset.slug in coverages:
                        spatial_coverages_found = 0
                        for coverage in coverages[dataset.slug]:
                            for spatial_coverage in spatial_coverages:
                                if coverage.area.slug.startswith(spatial_coverage):
                                    spatial_coverages_found += 1
                                    break
                            if spatial_coverages_found == len(spatial_coverages):
                                new_dataset_list.append(dataset)
                                break
            dataset_list = new_dataset_list
        if "temporal_coverage" in req_args:
            # Filter by temporal coverage
            temporal_coverage = req_args["temporal_coverage"]
            start_year, end_year = temporal_coverage.split("-")
            start_year = int(start_year)
            end_year = int(end_year)
            new_dataset_list = []
            added_datasets = set()
            for dataset in dataset_list:
                if dataset.slug in coverages:
                    for coverage in coverages[dataset.slug]:
                        for datetime_range in coverage.datetime_ranges.all():
                            if (
                                datetime_range.start_year <= start_year
                                and datetime_range.end_year >= end_year
                            ):
                                new_dataset_list.append(dataset)
                                added_datasets.add(dataset.slug)
                                break
                        if dataset.slug in added_datasets:
                            break
            dataset_list = new_dataset_list
        if "entity" in req_args:
            # Collect all entities
            entities: Dict[str, List[str]] = {}
            added_entities = set()
            for dataset in dataset_list:
                for table in dataset.tables.all():
                    for observation_level in table.observation_levels.all():
                        entity = observation_level.entity
                        if entity.id not in added_entities:
                            if dataset.slug not in entities:
                                entities[dataset.slug] = []
                            entities[dataset.slug].append(entity.slug)
                            added_entities.add(entity.id)
                for raw_data_source in dataset.raw_data_sources.all():
                    for observation_level in raw_data_source.observation_levels.all():
                        entity = observation_level.entity
                        if entity.id not in added_entities:
                            if dataset.slug not in entities:
                                entities[dataset.slug] = []
                            entities[dataset.slug].append(entity.slug)
                            added_entities.add(entity.id)
                for information_request in dataset.information_requests.all():
                    for (
                        observation_level
                    ) in information_request.observation_levels.all():
                        entity = observation_level.entity
                        if entity.id not in added_entities:
                            if dataset.slug not in entities:
                                entities[dataset.slug] = []
                            entities[dataset.slug].append(entity.slug)
                            added_entities.add(entity.id)
            # Filter by entity slugs
            entity_slugs = req_args.getlist("entity")
            new_dataset_list = []
            if filter_method == "or":
                for dataset in dataset_list:
                    for entity_slug in entity_slugs:
                        if (
                            dataset.slug in entities
                            and entity_slug in entities[dataset.slug]
                        ):
                            new_dataset_list.append(dataset)
                            break
            elif filter_method == "and":
                for dataset in dataset_list:
                    entities_found = 0
                    for entity_slug in entity_slugs:
                        if (
                            dataset.slug in entities
                            and entity_slug in entities[dataset.slug]
                        ):
                            entities_found += 1
                    if entities_found == len(entity_slugs):
                        new_dataset_list.append(dataset)
            dataset_list = new_dataset_list
        if "update_frequency" in req_args:
            update_frequencies: List[Tuple[int, str]] = [
                self.split_number_text(frequency)
                for frequency in req_args.getlist("update_frequency")
            ]
            # Collect all updates
            updates: Dict[str, List[Tuple[int, str]]] = {}
            added_updates = set()
            for dataset in dataset_list:
                for table in dataset.tables.all():
                    for update in table.updates.all():
                        if update.id not in added_updates:
                            if dataset.slug not in updates:
                                updates[dataset.slug] = []
                            updates[dataset.slug].append(
                                (update.frequency, update.entity.slug)
                            )
                            added_updates.add(update.id)
                for raw_data_source in dataset.raw_data_sources.all():
                    for update in raw_data_source.updates.all():
                        if update.id not in added_updates:
                            if dataset.slug not in updates:
                                updates[dataset.slug] = []
                            updates[dataset.slug].append(
                                (update.frequency, update.entity.slug)
                            )
                            added_updates.add(update.id)
                for information_request in dataset.information_requests.all():
                    for update in information_request.updates.all():
                        if update.id not in added_updates:
                            if dataset.slug not in updates:
                                updates[dataset.slug] = []
                            updates[dataset.slug].append(
                                (update.frequency, update.entity.slug)
                            )
                            added_updates.add(update.id)
            # Filter by update frequencies
            new_dataset_list = []
            if filter_method == "or":
                for dataset in dataset_list:
                    for update_frequency in update_frequencies:
                        if (
                            dataset.slug in updates
                            and update_frequency in updates[dataset.slug]
                        ):
                            new_dataset_list.append(dataset)
                            break
            elif filter_method == "and":
                return HttpResponseBadRequest(
                    json.dumps(
                        {
                            "error": "Invalid filter method: 'and' not supported for 'update_frequency'"
                        }
                    )
                )
            dataset_list = new_dataset_list
        if "raw_quality_tier" in req_args:
            # TODO: filter by raw quality tier
            ...

        return dataset_list

    def paginate_results(self, dataset_list: List[Dataset], req_args: Dict[str, str]):
        # Pagination
        print("dataset list", dataset_list)
        try:
            if "page_size" in req_args:
                page_size = int(req_args["page_size"])
            else:
                page_size = 10
            if page_size < 1:
                raise ValueError("page_size must be greater than 0")
        except:  # noqa
            return HttpResponseBadRequest(json.dumps({"error": "Invalid page_size"}))
        try:
            if "page" in req_args:
                page = int(req_args["page"])
            else:
                page = 1
            if page < 1:
                raise ValueError("page must be greater than 0")
        except:  # noqa
            return HttpResponseBadRequest(json.dumps({"error": "Invalid page"}))
        page_dataset_list = dataset_list[
            (page - 1) * page_size : page * page_size  # noqa
        ]
        results = [ds for ds in page_dataset_list]
        return results

    def serialize_dataset(self, dataset: Dataset):
        def get_temporal_coverage(dataset: Dataset) -> str:
            min_year = float("inf")
            max_year = float("-inf")
            datetimes = []
            added_datetime_ids = set()
            added_coverages = set()
            for table in dataset.tables.all():
                for coverage in table.coverages.all():
                    if coverage.id not in added_coverages:
                        for datetime_range in coverage.datetime_ranges.all():
                            if datetime_range.id not in added_datetime_ids:
                                datetimes.append(datetime_range)
                                added_datetime_ids.add(datetime_range.id)
            for raw_data_source in dataset.raw_data_sources.all():
                for coverage in raw_data_source.coverages.all():
                    if coverage.id not in added_coverages:
                        for datetime_range in coverage.datetime_ranges.all():
                            if datetime_range.id not in added_datetime_ids:
                                datetimes.append(datetime_range)
                                added_datetime_ids.add(datetime_range.id)
            for information_request in dataset.information_requests.all():
                for coverage in information_request.coverages.all():
                    if coverage.id not in added_coverages:
                        for datetime_range in coverage.datetime_ranges.all():
                            if datetime_range.id not in added_datetime_ids:
                                datetimes.append(datetime_range)
                                added_datetime_ids.add(datetime_range.id)
            for datetime_range in datetimes:
                min_year = min(min_year, datetime_range.start_year)
                max_year = max(max_year, datetime_range.end_year)

            if min_year == max_year:
                return f"{min_year}"
            return f"{min_year}-{max_year}"

        def get_themes(dataset: Dataset) -> List[Dict[str, str]]:
            themes = []
            for theme in dataset.themes.all():
                themes.append(
                    {
                        "name": theme.name,
                        "slug": theme.slug,
                    }
                )
            return themes

        def get_tags(dataset: Dataset) -> List[Dict[str, str]]:
            tags = []
            for tag in dataset.tags.all():
                tags.append(
                    {
                        "name": tag.name,
                        "slug": tag.slug,
                    }
                )
            return tags

        def get_first_table_id(dataset: Dataset) -> Union[str, None]:
            if dataset.tables.count() > 0:
                return str(dataset.tables.first().id)
            return None

        def get_first_original_source_id(dataset: Dataset) -> Union[str, None]:
            if dataset.raw_data_sources.count() > 0:
                return str(dataset.raw_data_sources.first().id)
            return None

        def get_first_lai_id(dataset: Dataset) -> Union[str, None]:
            if dataset.information_requests.count() > 0:
                return str(dataset.information_requests.first().id)
            return None

        organization_picture = dataset.organization.picture
        if organization_picture:
            organization_picture = organization_picture.url
        else:
            organization_picture = None

        return {
            "id": str(dataset.id),
            "slug": dataset.slug,
            "full_slug": dataset.full_slug,
            "name": dataset.name,
            "description": dataset.description,
            "organization": dataset.organization.name,
            "organization_slug": dataset.organization.slug,
            "organization_picture": organization_picture,
            "organization_website": dataset.organization.website,
            "themes": get_themes(dataset),
            "tags": get_tags(dataset),
            "temporal_coverage": get_temporal_coverage(dataset),
            "n_bdm_tables": dataset.tables.count(),
            "first_table_id": get_first_table_id(dataset),
            "n_original_sources": dataset.raw_data_sources.count(),
            "first_original_source_id": get_first_original_source_id(dataset),
            "n_lais": dataset.information_requests.count(),
            "first_lai_id": get_first_lai_id(dataset),
            "is_closed": dataset.is_closed,
        }

    def get_context_data(self, **kwargs):
        kwargs.setdefault("view", self)
        if self.extra_context is not None:
            kwargs.update(self.extra_context)
        return kwargs

    def split_number_text(self, text: str) -> Tuple[int, str]:
        """
        Splits a string into a number and text part. Examples:
        >>> split_number_text("1year")
        (1, 'year')
        >>> split_number_text("2 month")
        (2, 'month')
        >>> split_number_text("3minute")
        (3, 'minute')
        """
        number = ""
        for c in text:
            if c.isdigit():
                number += c
            else:
                break
        if number == "":
            return None, text
        return int(number), (text[len(number) :]).strip()  # noqa
