# -*- coding: utf-8 -*-

from django.core.files.storage import default_storage as storage
from django.http import JsonResponse
from haystack.forms import FacetedSearchForm
from haystack.generic_views import FacetedSearchView
from haystack.models import SearchResult
from haystack.query import SearchQuerySet

from backend.apps.api.v1.models import Entity, Organization, Tag, Theme


import logging
logger = logging.getLogger(__name__)
class DatasetSearchForm(FacetedSearchForm):
    load_all: bool = True

    def __init__(self, *args, **kwargs):
        self.contains = kwargs.pop("contains", None) or []
        self.tag = kwargs.pop("tag", None) or []
        self.theme = kwargs.pop("theme", None) or []
        self.organization = kwargs.pop("organization", None) or []
        self.observation_level = kwargs.pop("observation_level", None) or []
        self.locale = kwargs.pop("locale", "pt")
        super().__init__(*args, **kwargs)

    def search(self):
        if not self.is_valid():
            return self.no_query_found()

        if q := self.cleaned_data.get("q"):
            sqs = (
                self.searchqueryset
                .auto_query(q)
                .filter_and(**{"text.edgengram": q})
                .filter_or(**{f"text.snowball_{self.locale}": q})
            )
        else:
            sqs = self.no_query_found()

        for qp_value in self.contains:
            sqs = sqs.narrow(f'contains_{qp_value}:"true"')

        for qp_key, facet_key in [
            ("tag", "tag_slug"),
            ("theme", "theme_slug"),
            ("observation_level", "entity_slug"),
            ("organization", "organization_slug"),
        ]:
            for qp_value in getattr(self, qp_key, []):
                sqs = sqs.narrow(f'{facet_key}:"{sqs.query.clean(qp_value)}"')

        return sqs

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

    @property
    def locale(self):
        return self.request.GET.get('locale', 'pt')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"contains": self.request.GET.getlist("contains")})
        kwargs.update({"tag": self.request.GET.getlist("tag")})
        kwargs.update({"theme": self.request.GET.getlist("theme")})
        kwargs.update({"organization": self.request.GET.getlist("organization")})
        kwargs.update({"observation_level": self.request.GET.getlist("observation_level")})
        kwargs.update({"locale": self.locale})
        return kwargs

    def get(self, request, *args, **kwargs):
        sqs = self.get_form().search()
        return JsonResponse(
            {
                "page": self.page,
                "page_size": self.page_size,
                "count": sqs.count(),
                "results": self.get_results(sqs),
                "aggregations": self.get_facets(sqs),
                "locale": self.locale,
            }
        )

    def get_facets(self, sqs: SearchQuerySet, facet_size=22):
        sqs = sqs.facet("tag_slug", size=facet_size)
        sqs = sqs.facet("theme_slug", size=facet_size)
        sqs = sqs.facet("entity_slug", size=facet_size)
        sqs = sqs.facet("organization_slug", size=facet_size)

        facets = {}
        facet_counts = sqs.facet_counts()
        facet_counts = facet_counts.get("fields", {}).items()
        for key, values in facet_counts:
            facets[key] = []
            for value in values:
                facets[key].append(
                    {
                        "key": value[0],
                        "count": value[1],
                    }
                )
        for key_back, key_front, model in [
            ("tag_slug", "tags", Tag),
            ("theme_slug", "themes", Theme),
            ("entity_slug", "observation_levels", Entity),
            ("organization_slug", "organizations", Organization),
        ]:
            to_name = model.objects.values("slug", f"name_{self.locale}", "name")
            to_name = {e["slug"]: {
                "name": e[f"name_{self.locale}"] or e["name"] or e["slug"],
                "fallback": e[f"name_{self.locale}"] is None
            } for e in to_name.all()}
            facets[key_front] = facets.pop(key_back, None)
            for field in facets[key_front] or []:
                translated_name = to_name.get(field["key"], {})
                field["name"] = translated_name.get("name", field["key"])
                field["fallback"] = translated_name.get("fallback", True)
        return facets

    def get_results(self, sqs: SearchQuerySet):
        def key(r):
            return (r.contains_tables, r.score, r.updated_at)

        until = self.page * self.page_size
        since = (self.page - 1) * self.page_size

        results = sorted(sqs.all(), key=key, reverse=True)
        return [as_search_result(r, self.locale) for r in results[since:until]]


def as_search_result(result: SearchResult, locale='pt'):
    
    tags = []
    for slug, name in zip(result.tag_slug or [], getattr(result, f"tag_name_{locale}") or []):
        tags.append(
            {
                "slug": slug,
                "name": name,
            }
        )

    themes = []
    for slug, name in zip(result.theme_slug or [], getattr(result, f"theme_name_{locale}") or []):
        themes.append(
            {
                "slug": slug,
                "name": name,
            }
        )

    entities = []
    for slug, name in zip(result.entity_slug or [], getattr(result, f"entity_name_{locale}") or []):
        entities.append(
            {
                "slug": slug,
                "name": name,
            }
        )

    organizations = []
    for pk, slug, name, picture in zip(
        result.organization_id or [],
        result.organization_slug or [],
        [(getattr(result, f"organization_name_{locale}") or []) or result.organization_name or result.organization_slug],
        result.organization_picture or [],
    ):
        picture = storage.url(picture)
        organizations.append(
            {
                "id": pk,
                "slug": slug,
                "name": name,
                "picture": picture,
            }
        )

    return {
        "updated_at": result.updated_at,
        "id": result.dataset_id,
        "slug": result.dataset_slug,
        "name": getattr(result, f"dataset_name_{locale}") or result.dataset_name or result.dataset_slug,
        "description": getattr(result, f"dataset_description_{locale}") or result.dataset_description,
        "tags": tags,
        "themes": themes,
        "entities": entities,
        "organizations": organizations,
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
