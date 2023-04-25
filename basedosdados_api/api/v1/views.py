# -*- coding: utf-8 -*-
import json
from typing import Dict, List, Tuple

from django.http import HttpResponse, HttpResponseBadRequest, QueryDict
from haystack.generic_views import SearchView

from basedosdados_api.api.v1.models import Coverage, Dataset


class DatasetSearchView(SearchView):
    def get(self, request, *args, **kwargs):
        """
        Handles GET requests and instantiates a blank version of the form.
        """
        # Get request arguments
        req_args: QueryDict = request.GET.copy()
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
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
            # Filtering
            if "theme" in req_args:
                # Filter by theme slugs
                theme_slugs = req_args.getlist("theme")
                new_dataset_list = []
                for dataset in dataset_list:
                    for theme in dataset.themes.all():
                        if theme.slug in theme_slugs:
                            new_dataset_list.append(dataset)
                            break
                dataset_list = new_dataset_list
            if "organization" in req_args:
                # Filter by organization slugs
                organization_slugs = req_args.getlist("organization")
                dataset_list = [
                    ds
                    for ds in dataset_list
                    if ds.organization.slug in organization_slugs
                ]
            if "tag" in req_args:
                # Filter by tag slugs
                tag_slugs = req_args.getlist("tag")
                new_dataset_list = []
                for dataset in dataset_list:
                    for tag in dataset.tags.all():
                        if tag.slug in tag_slugs:
                            new_dataset_list.append(dataset)
                            break
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
                        for (
                            observation_level
                        ) in raw_data_source.observation_levels.all():
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
                for dataset in dataset_list:
                    for entity_slug in entity_slugs:
                        if (
                            dataset.slug in entities
                            and entity_slug in entities[dataset.slug]
                        ):
                            new_dataset_list.append(dataset)
                            break
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
                for dataset in dataset_list:
                    for update_frequency in update_frequencies:
                        if (
                            dataset.slug in updates
                            and update_frequency in updates[dataset.slug]
                        ):
                            new_dataset_list.append(dataset)
                            break
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
                return HttpResponseBadRequest(
                    json.dumps({"error": "Invalid page_size"})
                )
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
        else:
            return HttpResponseBadRequest(json.dumps({"error": "Invalid form"}))

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

        return {
            "id": str(dataset.id),
            "slug": dataset.slug,
            "full_slug": dataset.full_slug,
            "name": dataset.name,
            "organization": dataset.organization.name,
            "temporal_coverage": get_temporal_coverage(dataset),
            "n_bdm_tables": dataset.tables.count(),
            "n_original_sources": dataset.raw_data_sources.count(),
            "n_lais": dataset.information_requests.count(),
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
