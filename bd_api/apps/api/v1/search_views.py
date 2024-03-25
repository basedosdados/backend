# -*- coding: utf-8 -*-
from django.http import JsonResponse
from haystack.forms import FacetedSearchForm
from haystack.generic_views import FacetedSearchView
from haystack.query import SearchQuerySet

from bd_api.apps.api.v1.models import Entity, Organization, Tag, Theme


class DatasetSearchForm(FacetedSearchForm):
    load_all: bool = True

    def no_query_found(self):
        return self.searchqueryset.all()


class DatasetSearchView(FacetedSearchView):
    form_class = DatasetSearchForm
    facet_fields = [
        "tag",
        "theme",
        "entity",
        "organization",
        "contains_open_data",
        "contains_closed_data",
        "contains_tables",
        "contains_raw_data_sources",
        "contains_information_requests",
    ]

    def get(self, request, *args, **kwargs):
        if form := self.get_form():
            if sqs := form.search():
                return JsonResponse(
                    {
                        "count": sqs.count(),
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
            for field in facets[key]:
                field["name"] = m[field["key"]]
        return facets

    def get_results(self, sqs: SearchQuerySet):
        def key(r):
            return (r.contains_tables, r.score)

        results = sorted(sqs.all(), key=key, reverse=True)
        return [r.object.as_search_result for r in results]
