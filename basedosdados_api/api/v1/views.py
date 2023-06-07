# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from typing import Tuple

from django.conf import settings
from django.http import HttpResponseBadRequest, QueryDict, JsonResponse
from haystack.forms import ModelSearchForm
from haystack.generic_views import SearchView

from elasticsearch import Elasticsearch

from basedosdados_api.api.v1.models import Organization, Theme, Tag, Table


class DatasetESSearchView(SearchView):
    def get(self, request, *args, **kwargs):
        """
        Handles GET requests and instantiates a blank version of the form.
        """
        # Get request arguments
        req_args: QueryDict = request.GET.copy()
        query = req_args.get("q", None)
        es = Elasticsearch(settings.HAYSTACK_CONNECTIONS["default"]["URL"])
        page_size = int(req_args.get("page_size", 10))
        page = int(req_args.get("page", 1))

        # If query is empty, query all datasets
        if not query:
            query = {"match_all": {}}
        else:
            query = {
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
            }

        all_filters = []

        if "organization" in req_args:
            all_filters.append(
                {"match": {"organization.slug.keyword": req_args.get("organization")}}
            )

        if "theme" in req_args:
            filter_theme = [
                {"match": {"themes_slug.keyword": theme}}
                for theme in req_args.getlist("theme")
            ]
            for t in filter_theme:
                all_filters.append(t)

        if "tag" in req_args:
            filter_tag = [
                {"match": {"tags_slug.keyword": tag}} for tag in req_args.getlist("tag")
            ]
            for t in filter_tag:
                all_filters.append(t)

        raw_query = {
            "from": (page - 1) * page_size,
            "size": page_size,
            "query": {
                "function_score": {
                    "query": {
                        "bool": {
                            "must": [
                                query,
                                {"bool": {"must": all_filters}},
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
            "aggs": {
                "themes_keyword_counts": {
                    "terms": {
                        "field": "themes_slug.keyword",
                        "size": 1000,
                    }
                },
                "is_closed_counts": {
                    "terms": {
                        "field": "is_closed",
                        "size": 1000,
                    }
                },
                "organization_counts": {
                    "terms": {
                        "field": "organization_slug.keyword",
                        "size": 1000,
                    }
                },
                "tags_slug_counts": {
                    "terms": {
                        "field": "tags_slug.keyword",
                        "size": 1000,
                    }
                },
                "temporal_coverage_counts": {"terms": {"field": "coverage.keyword"}},
                "observation_levels_counts": {
                    "terms": {
                        "field": "observation_levels.keyword",
                        "size": 1000,
                    }
                },
                "contains_tables_counts": {
                    "terms": {
                        "field": "contains_tables",
                        "size": 1000,
                    }
                },
                "contains_raw_data_sources_counts": {
                    "terms": {
                        "field": "contains_raw_data_sources",
                        "size": 1000,
                    }
                },
                "contains_information_requests_counts": {
                    "terms": {
                        "field": "contains_information_requests",
                        "size": 1000,
                    }
                },
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
        for idx, result in enumerate(es_results):
            r = result.get("_source")
            cleaned_results = {}
            cleaned_results["id"] = r.get("django_id")
            cleaned_results["slug"] = r.get("slug")
            cleaned_results["name"] = r.get("name")
            # cleaned_results["description"] = r.get("description")

            # organization
            organization = r.get("organization", [])
            # soon this will become a many to many relationship
            # for now, we just put the organization within a list
            organization = [organization] if organization else []
            if len(organization) > 0:
                cleaned_results["organization"] = []
                for _, org in enumerate(organization):
                    picture_url = ""
                    try:
                        org_object: Organization = Organization.objects.get(
                            id=org["id"]
                        )
                        if org_object.picture is not None:
                            picture_url = org_object.picture.url
                    except Organization.DoesNotExist:
                        pass
                    except ValueError:
                        pass
                    d = {
                        "id": org["id"],
                        "name": org["name"],
                        "slug": org["slug"],
                        "picture": picture_url,
                        "website": org["website"],
                        "description": org["description"],
                    }
                    cleaned_results["organization"].append(d)

            # themes
            if r.get("themes"):
                cleaned_results["themes"] = []
                for idx, theme in enumerate(r.get("themes")):
                    d = {"name": theme["name"], "slug": theme["keyword"]}
                    cleaned_results["themes"].append(d)
            # tags
            if r.get("tags"):
                cleaned_results["tags"] = []
                for idx, tag in enumerate(r.get("tags")):
                    d = {"name": tag["name"], "slug": tag["keyword"]}
                    cleaned_results["tags"].append(d)

            # tables
            if r.get("tables"):
                cleaned_results["tables"] = []
                for idx, table in enumerate(r.get("tables")):
                    d = {
                        "id": table["id"],
                        "name": table["name"],
                        "slug": table["slug"],
                    }
                    cleaned_results["tables"].append(d)
                if len(cleaned_results["tables"]) > 0:
                    cleaned_results["first_table_id"] = cleaned_results["tables"][0][
                        "id"
                    ]
                    cleaned_results["n_tables"] = len(cleaned_results["tables"])
                    closed_tables = [
                        t
                        for t in cleaned_results["tables"]
                        if Table.objects.get(id=t["id"]).is_closed
                    ]
                    cleaned_results["n_closed_tables"] = len(closed_tables)

            # observation levels
            if r.get("observation_levels"):
                cleaned_results["entities"] = r.get("observation_levels")

            # raw data sources
            cleaned_results["n_raw_data_sources"] = r.get("n_raw_data_sources", 0)
            cleaned_results["first_raw_data_source_id"] = r.get(
                "first_raw_data_source_id", []
            )

            # information requests
            cleaned_results["n_information_requests"] = r.get(
                "n_information_requests", 0
            )
            cleaned_results["first_information_request_id"] = r.get(
                "first_information_request_id", []
            )

            # temporal coverage
            coverage = r.get("coverage")
            if coverage:
                if coverage[0] == " - ":
                    coverage = ""
                elif "inf" in coverage[0]:
                    coverage = coverage.replace("inf", "")
                cleaned_results["temporal_coverage"] = coverage
                del r["coverage"]
            else:
                cleaned_results["temporal_coverage"] = ""
            res.append(cleaned_results)

        # Aggregations
        agg = context["object_list"].get("aggregations")
        organization_counts = agg["organization_counts"]["buckets"]
        themes_slug_counts = agg["themes_keyword_counts"]["buckets"]
        tags_slug_counts = agg["tags_slug_counts"]["buckets"]
        # temporal_coverage_counts = agg["temporal_coverage_counts"]["buckets"]
        observation_levels_counts = agg["observation_levels_counts"]["buckets"]
        is_closed_counts = agg["is_closed_counts"]["buckets"]
        contains_tables_counts = agg["contains_tables_counts"]["buckets"]
        contains_information_requests_counts = agg[
            "contains_information_requests_counts"
        ]["buckets"]
        contains_raw_data_sources_counts = agg["contains_raw_data_sources_counts"][
            "buckets"
        ]

        # Return results
        aggregations = dict()
        if organization_counts:
            agg_organizations = [
                {
                    "key": org["key"],
                    "count": org["doc_count"],
                    # TODO: This error makes absolutely no sense, but it's the only way to make it work
                    "name": Organization.objects.filter(slug=org["key"])[0].name,
                }
                for idx, org in enumerate(organization_counts)
            ]
            aggregations["organizations"] = agg_organizations

        if themes_slug_counts:
            agg_themes = [
                {
                    "key": theme["key"],
                    "count": theme["doc_count"],
                    "name": Theme.objects.get(slug=theme["key"]).name,
                }
                for idx, theme in enumerate(themes_slug_counts)
            ]
            aggregations["themes"] = agg_themes

        if tags_slug_counts:
            agg_tags = [
                {
                    "key": tag["key"],
                    "count": tag["doc_count"],
                    "name": Tag.objects.get(slug=tag["key"]).name,
                }
                for idx, tag in enumerate(tags_slug_counts)
            ]
            aggregations["tags"] = agg_tags

        if observation_levels_counts:
            agg_observation_levels = [
                {
                    "key": observation_level["key"],
                    "count": observation_level["doc_count"],
                    "name": observation_level["key"],
                }
                for idx, observation_level in enumerate(observation_levels_counts)
            ]
            aggregations["observation_levels"] = agg_observation_levels

        if is_closed_counts:
            agg_is_closed = [
                {
                    "key": is_closed["key"],
                    "count": is_closed["doc_count"],
                    "name": "closed" if is_closed["key"] == 0 else "open",
                }
                for idx, is_closed in enumerate(is_closed_counts)
            ]
            aggregations["is_closed"] = agg_is_closed

        if contains_tables_counts:
            agg_contains_tables = [
                {
                    "key": contains_tables["key"],
                    "count": contains_tables["doc_count"],
                    "name": "tabelas tratadas"
                    if contains_tables["key"] == 1
                    else "sem tabelas tratadas",
                }
                for idx, contains_tables in enumerate(contains_tables_counts)
            ]
            aggregations["contains_tables"] = agg_contains_tables

        if contains_information_requests_counts:
            agg_contains_information_requests = [
                {
                    "key": contains_information_requests["key"],
                    "count": contains_information_requests["doc_count"],
                    "name": "pedidos lai"
                    if contains_information_requests["key"] == 1
                    else "sem pedidos lai",
                }
                for idx, contains_information_requests in enumerate(
                    contains_information_requests_counts
                )
            ]
            aggregations[
                "contains_information_requests"
            ] = agg_contains_information_requests

        if contains_raw_data_sources_counts:
            agg_contains_raw_data_sources = [
                {
                    "key": contains_raw_data_sources["key"],
                    "count": contains_raw_data_sources["doc_count"],
                    "name": "fontes originais"
                    if contains_raw_data_sources["key"] == 1
                    else "sem fontes originais",
                }
                for idx, contains_raw_data_sources in enumerate(
                    contains_raw_data_sources_counts
                )
            ]
            aggregations["contains_raw_data_sources"] = agg_contains_raw_data_sources

        results = {"count": count, "results": res, "aggregations": aggregations}
        max_score = context["object_list"].get("hits").get("max_score")  # noqa

        return JsonResponse(
            results,
            status=200 if len(results) > 0 else 204,
        )

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
