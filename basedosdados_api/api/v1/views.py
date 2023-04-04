# -*- coding: utf-8 -*-
import json
from typing import List

from django.http import HttpResponse, HttpResponseBadRequest
from haystack.generic_views import SearchView

from basedosdados_api.api.v1.models import Dataset


class DatasetSearchView(SearchView):
    def get(self, request, *args, **kwargs):
        """
        Handles GET requests and instantiates a blank version of the form.
        """
        # Get request arguments
        req_args = request.GET.copy()
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
            # TODO: filter by other stuff
            if "group" in req_args:
                # TODO: filter by theme
                ...
            if "organization" in req_args:
                # TODO: filter by organization
                ...
            if "tag" in req_args:
                # TODO: filter by tag
                ...
            if "spatial_coverage" in req_args:
                # TODO: filter by spatial coverage
                ...
            if "temporal_coverage" in req_args:
                # TODO: filter by temporal coverage
                ...
            if "entity" in req_args:
                # TODO: filter by observation level / entity
                ...
            if "update_frequency" in req_args:
                # TODO: filter by update frequency
                ...
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

    def serialize_dataset(self, dataset):
        return {
            "id": str(dataset.id),
            "slug": dataset.slug,
            "full_slug": dataset.full_slug,
            "name": dataset.name,
            "organization": dataset.organization.name,
            "temporal_coverage": "TODO.",  # TODO
            "n_bdm_tables": "TODO.",  # TODO
            "n_original_sources": "TODO.",  # TODO
            "n_lais": "TODO.",  # TODO
        }

    def get_context_data(self, **kwargs):
        kwargs.setdefault("view", self)
        if self.extra_context is not None:
            kwargs.update(self.extra_context)
        return kwargs
