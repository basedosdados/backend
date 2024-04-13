# -*- coding: utf-8 -*-
from django.http import JsonResponse
from haystack.forms import FacetedSearchForm
from haystack.generic_views import FacetedSearchView
from haystack.models import SearchResult
from haystack.query import SearchQuerySet

from bd_api.apps.api.v1.models import Entity, Organization, Tag, Theme


class DatasetSearchForm(FacetedSearchForm):
    load_all: bool = True

    def no_query_found(self):
        return self.searchqueryset.all()


class DatasetSearchView(FacetedSearchView):
    form_class = DatasetSearchForm
    facet_fields = [
        "tag_slug",
        "theme_slug",
        "entity_slug",
        "organization_slug",
        "contains_open_data",
        "contains_closed_data",
        "contains_tables",
        "contains_raw_data_sources",
        "contains_information_requests",
    ]

    @property
    def page(self):
        try:
            return int(self.request.GET.get("page", 1))
        except (TypeError, ValueError):
            return 1

    @property
    def page_size(self):
        try:
            return int(self.request.GET.get("page_size", 10))
        except (TypeError, ValueError):
            return 10

    def get(self, request, *args, **kwargs):
        if form := self.get_form():
            if sqs := form.search():
                return JsonResponse(
                    {
                        "count": sqs.count(),
                        "page": self.page,
                        "page_size": self.page_size,
                        "results": self.get_results(sqs),
                        "aggregations": self.get_facets(sqs),
                    }
                )

    def get_facets(self, sqs: SearchQuerySet):
        facets = {}
        for key, values in sqs.facet_counts()["fields"].items():
            facets[key] = []
            for value in values:
                facets[key].append(
                    {
                        "key": value[0],
                        "count": value[1],
                    }
                )
        for key, model in [
            ("tag", Tag),
            ("theme", Theme),
            ("entity", Entity),
            ("organization", Organization),
        ]:
            m = model.objects.values("slug", "name")
            m = {mi["slug"]: mi["name"] for mi in m.all()}
            facets[key] = facets.pop(f"{key}_slug", None)
            for field in facets[key]:
                field["name"] = m.get(field["key"], "")
            facets["observation_level"] = facets.pop("entity", None)
        return facets

    def get_results(self, sqs: SearchQuerySet):
        def key(r):
            return (r.contains_tables, r.score)

        until = self.page * self.page_size
        since = (self.page - 1) * self.page_size

        results = sorted(sqs.all(), key=key, reverse=True)
        return [as_search_result(r) for r in results[since:until]]


def as_search_result(result: SearchResult):
    tag = []
    for slug, name in zip(result.tag_slug, result.tag_name):
        tag.append(
            {
                "slug": slug,
                "name": name,
            }
        )

    theme = []
    for slug, name in zip(result.theme_slug, result.theme_name):
        theme.append(
            {
                "slug": slug,
                "name": name,
            }
        )

    entity = []
    for slug, name in zip(result.entity_slug, result.entity_name):
        entity.append(
            {
                "slug": slug,
                "name": name,
            }
        )

    organization = []
    for pk, slug, name, picture, website, description in zip(
        result.organization_id,
        result.organization_slug,
        result.organization_name,
        result.organization_picture,
        result.organization_website,
        result.organization_description,
    ):
        organization.append(
            {
                "id": pk,
                "slug": slug,
                "name": name,
                "picture": picture,
                "website": website,
                "description": description,
            }
        )

    return {
        "updated_at": result.updated_at,
        "id": result.dataset_id,
        "slug": result.dataset_slug,
        "name": result.dataset_name,
        "description": result.dataset_description,
        "tags": tag,
        "themes": theme,
        "entities": entity,
        "organizations": organization,
        "temporal_coverages": result.temporal_coverage,
        "contains_open_data": result.contains_open_data,
        "contains_closed_data": result.contains_closed_data,
        "contains_tables": result.contains_tables,
        "contains_raw_data_sources": result.contains_raw_data_sources,
        "contains_information_requests": result.contains_information_requests,
        "n_tables": result.n_tables,
        "n_raw_data_sources": result.n_raw_data_sources,
        "n_information_requests": result.n_information_requests,
        "first_table_id": result.first_table_id,
        "first_open_table_id": result.first_open_table_id,
        "first_closed_table_id": result.first_closed_table_id,
        "first_raw_data_source_id": result.first_raw_data_source_id,
        "first_information_request_id": result.first_information_request_id,
    }
