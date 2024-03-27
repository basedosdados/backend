# -*- coding: utf-8 -*-
from django.http import JsonResponse
from haystack.forms import FacetedSearchForm
from haystack.generic_views import FacetedSearchView


class DatasetSearchForm(FacetedSearchForm):
    """Dataset search form

    Note that `load_all=True` avoids lazy loading and possible N+1 problem
    """

    load_all = True

    @property
    def query(self):
        return self.cleaned_data

    @property
    def facet(self):
        return self.sqs.facet_counts()

    @property
    def result(self):
        return [p.pk for p in self.sqs]

    @property
    def response(self):
        return {
            "query": self.query,
            "facet": self.facet,
            "result": self.result,
        }

    def search(self):
        self.sqs = super().search()

        if not self.is_valid():
            return self.no_query_found()

    def no_query_found(self):
        return self.searchqueryset.all()


class DatasetSearchView(FacetedSearchView):
    form_class = DatasetSearchForm
    facet_fields = ["tag_slugs", "theme_slugs"]

    def get(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            form.search()
            return JsonResponse(form.response, status=200)
        else:
            return JsonResponse({"errors": form.errors}, status=400)
