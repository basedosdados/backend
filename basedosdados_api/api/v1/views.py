# -*- coding: utf-8 -*-
from __future__ import annotations

import json

from django.conf import settings
from django.core.files.storage import get_storage_class
from django.http import HttpResponseBadRequest, QueryDict, JsonResponse
from haystack.forms import ModelSearchForm
from haystack.generic_views import SearchView

from elasticsearch import Elasticsearch

from basedosdados_api.api.v1.models import (
    Organization,
    Theme,
    Entity,
)


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
        # As counts are paginated, we need to get the total number of results
        agg_page_size = 1000

        storage = get_storage_class()

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
                        {"match": {"name.edgengram": query}},
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

        if "contains_table" in req_args:
            all_filters.append(
                {"match": {"contains_tables": req_args.get("contains_table")}}
            )

        if "observation_level" in req_args:
            all_filters.append(
                {
                    "match": {
                        "observation_levels.keyword": req_args.get("observation_level")
                    }
                }
            )

        if "datasets_with" or "contains" in req_args:
            if "datasets_with" in req_args:
                options = req_args.getlist("datasets_with")
            else:
                options = req_args.getlist("contains")
            if "tables" in options:
                all_filters.append({"match": {"contains_tables": True}})
            if "closed_data" in options:
                all_filters.append({"match": {"contains_closed_data": True}})
            if "open_data" in options:
                all_filters.append({"match": {"contains_open_data": True}})
            if "raw_data_sources" in options:
                all_filters.append({"match": {"contains_raw_data_sources": True}})
            if "information_requests" in options:
                all_filters.append({"match": {"contains_information_requests": True}})
            if "open_tables" in options:
                all_filters.append({"match": {"contains_open_tables": True}})
            if "closed_tables" in options:
                all_filters.append({"match": {"contains_closed_tables": True}})

        raw_query = {
            "from": (page - 1) * page_size,
            "size": page_size,
            "query": {
                "function_score": {
                    "query": {
                        "bool": {
                            "must": [
                                query,
                                {
                                    "bool": {
                                        "must": all_filters,
                                        "must_not": [
                                            {
                                                "match": {
                                                    "status_slug.exact": "under_review"
                                                }
                                            }
                                        ],
                                    }
                                },
                            ]
                        }
                    },
                    "field_value_factor": {
                        "field": "contains_tables",
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
                        "size": agg_page_size,
                    }
                },
                "is_closed_counts": {
                    "terms": {
                        "field": "is_closed",
                        "size": agg_page_size,
                    }
                },
                "organization_counts": {
                    "terms": {
                        "field": "organization_slug.keyword",
                        "size": agg_page_size,
                    }
                },
                "tags_slug_counts": {
                    "terms": {
                        "field": "tags_slug.keyword",
                        "size": agg_page_size,
                    }
                },
                "temporal_coverage_counts": {
                    "terms": {
                        "field": "coverage.keyword",
                        "size": agg_page_size,
                    }
                },
                "observation_levels_counts": {
                    "terms": {
                        "field": "observation_levels_keyword.keyword",
                        "size": agg_page_size,
                    }
                },
                "contains_tables_counts": {
                    "terms": {
                        "field": "contains_tables",
                        "size": agg_page_size,
                    }
                },
                "contains_closed_data_counts": {
                    "terms": {
                        "field": "contains_closed_data",
                        "size": agg_page_size,
                    }
                },
                "contains_open_data_counts": {
                    "terms": {
                        "field": "contains_open_data",
                        "size": agg_page_size,
                    }
                },
                "contains_open_tables_counts": {
                    "terms": {
                        "field": "contains_open_tables",
                        "size": agg_page_size,
                    }
                },
                "contains_closed_tables_counts": {
                    "terms": {
                        "field": "contains_closed_tables",
                        "size": agg_page_size,
                    }
                },
                "contains_raw_data_sources_counts": {
                    "terms": {
                        "field": "contains_raw_data_sources",
                        "size": agg_page_size,
                    }
                },
                "contains_information_requests_counts": {
                    "terms": {
                        "field": "contains_information_requests",
                        "size": agg_page_size,
                    }
                },
            },
            "sort": [
                {"_score": {"order": "desc"}},
                {"updated_at": {"order": "desc"}},
            ],
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
            cleaned_results = {
                "id": r.get("django_id"),
                "slug": r.get("slug"),
                "name": r.get("name"),
            }

            if r.get("updated_at"):
                cleaned_results["updated_at"] = r.get("updated_at")

            # organization
            organization = r.get("organization", [])
            # soon this will become a many-to-many relationship
            # for now, we just put the organization within a list
            organization = [organization] if organization else []
            if len(organization) > 0:
                cleaned_results["organization"] = []
                for _, org in enumerate(organization):
                    if "picture" in org:
                        picture = storage().url(org["picture"])
                    else:
                        picture = ""
                    d = {
                        "id": org["id"],
                        "name": org["name"],
                        "slug": org["slug"],
                        "picture": picture,
                        "website": org["website"],
                        "description": org["description"],
                    }
                    cleaned_results["organization"].append(d)

            # themes
            if r.get("themes"):
                cleaned_results["themes"] = []
                for theme in r.get("themes"):
                    d = {"name": theme["name"], "slug": theme["keyword"]}
                    cleaned_results["themes"].append(d)
            # tags
            if r.get("tags"):
                cleaned_results["tags"] = []
                for tag in r.get("tags"):
                    d = {"name": tag["name"], "slug": tag["keyword"]}
                    cleaned_results["tags"].append(d)

            # tables
            cleaned_results["n_closed_tables"] = r.get("n_closed_tables") or 0
            if r.get("tables"):
                if len(tables := r.get("tables")) > 0:
                    cleaned_results["first_table_id"] = tables[0]["id"]
                    cleaned_results["n_tables"] = len(tables)
                    cleaned_results["n_open_tables"] = (
                        cleaned_results["n_tables"] - cleaned_results["n_closed_tables"]
                    )
                    cleaned_results["first_closed_table_id"] = None
                    for table in tables:
                        if table["is_closed"]:
                            cleaned_results["first_closed_table_id"] = table["id"]
                            break

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

            # boolean fields
            cleaned_results["is_closed"] = r.get("is_closed", False)
            cleaned_results["contains_tables"] = r.get("contains_tables", False)
            cleaned_results["contains_closed_data"] = r.get(
                "contains_closed_data", False
            )
            cleaned_results["contains_open_data"] = r.get("contains_open_data", False)
            cleaned_results["contains_closed_tables"] = r.get(
                "contains_closed_tables", False
            )
            cleaned_results["contains_open_tables"] = r.get(
                "contains_open_tables", False
            )

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
        contains_closed_data_counts = agg["contains_closed_data_counts"]["buckets"]
        contains_open_data_counts = agg["contains_open_data_counts"]["buckets"]
        contains_open_tables_counts = agg["contains_open_tables_counts"]["buckets"]
        contains_closed_tables_counts = agg["contains_closed_tables_counts"]["buckets"]
        contains_information_requests_counts = agg[
            "contains_information_requests_counts"
        ]["buckets"]
        contains_raw_data_sources_counts = agg["contains_raw_data_sources_counts"][
            "buckets"
        ]

        # Getting data from DB to aggregate
        orgs = Organization.objects.all().values("slug", "name", "picture")
        orgs_dict = {}
        for org in orgs:
            slug = str(org.pop("slug"))
            orgs_dict[slug] = org

        themes = Theme.objects.all().values("slug", "name")
        themes_dict = {}
        for theme in themes:
            slug = str(theme.pop("slug"))
            themes_dict[slug] = theme

        entities = Entity.objects.all().values("slug", "name")
        entities_dict = {}
        for entity in entities:
            slug = str(entity.pop("slug"))
            entities_dict[slug] = entity

        # Return results
        aggregations = dict()
        if organization_counts:
            agg_organizations = [
                {
                    "key": org["key"],
                    "count": org["doc_count"],
                    "name": orgs_dict.get(org["key"]).get("name")
                    if orgs_dict.get(org["key"])
                    else org["key"],
                }
                for org in organization_counts
            ]
            aggregations["organizations"] = agg_organizations

        if themes_slug_counts:
            agg_themes = [
                {
                    "key": theme["key"],
                    "count": theme["doc_count"],
                    "name": themes_dict[theme["key"]]["name"],
                }
                for idx, theme in enumerate(themes_slug_counts)
            ]
            aggregations["themes"] = agg_themes

        if tags_slug_counts:
            agg_tags = [
                {
                    "key": tag["key"],
                    "count": tag["doc_count"],
                    "name": tag["key"],
                }
                for tag in tags_slug_counts
            ]
            aggregations["tags"] = agg_tags

        if observation_levels_counts:
            agg_observation_levels = [
                {
                    "key": observation_level["key"],
                    "count": observation_level["doc_count"],
                    "name": entities_dict[observation_level["key"]]["name"],
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

        if contains_closed_data_counts:
            agg_contains_closed_data = [
                {
                    "key": contains_closed_data["key"],
                    "count": contains_closed_data["doc_count"],
                    "name": "dados fechados"
                    if contains_closed_data["key"] == 1
                    else "sem dados fechados",
                }
                for idx, contains_closed_data in enumerate(contains_closed_data_counts)
            ]
            aggregations["contains_closed_data"] = agg_contains_closed_data

        if contains_open_data_counts:
            agg_contains_open_data = [
                {
                    "key": contains_open_data["key"],
                    "count": contains_open_data["doc_count"],
                    "name": "dados abertos"
                    if contains_open_data["key"] == 1
                    else "sem dados abertos",
                }
                for idx, contains_open_data in enumerate(contains_open_data_counts)
            ]
            aggregations["contains_open_data"] = agg_contains_open_data

        if contains_open_tables_counts:
            agg_contains_open_tables = [
                {
                    "key": contains_open_tables["key"],
                    "count": contains_open_tables["doc_count"],
                    "name": "tabelas abertas"
                    if contains_open_tables["key"] == 1
                    else "sem tabelas abertas",
                }
                for idx, contains_open_tables in enumerate(contains_open_tables_counts)
            ]
            aggregations["contains_open_tables"] = agg_contains_open_tables

        if contains_closed_tables_counts:
            agg_contains_closed_tables = [
                {
                    "key": contains_closed_tables["key"],
                    "count": contains_closed_tables["doc_count"],
                    "name": "tabelas fechadas"
                    if contains_closed_tables["key"] == 1
                    else "sem tabelas fechadas",
                }
                for idx, contains_closed_tables in enumerate(
                    contains_closed_tables_counts
                )
            ]
            aggregations["contains_closed_tables"] = agg_contains_closed_tables

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
