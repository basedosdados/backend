# -*- coding: utf-8 -*-

from django.core.files.storage import default_storage as storage
from django.http import JsonResponse
from django.views import View
from haystack.forms import FacetedSearchForm
from haystack.generic_views import FacetedSearchView
from haystack.models import SearchResult
from haystack.query import SearchQuerySet

from backend.apps.api.v1.models import Area, Entity, Organization, Tag, Theme


class DatasetSearchForm(FacetedSearchForm):
    load_all: bool = True

    def __init__(self, *args, **kwargs):
        self.contains = kwargs.pop("contains", None) or []
        self.theme = kwargs.pop("theme", None) or []
        self.organization = kwargs.pop("organization", None) or []
        self.spatial_coverage = kwargs.pop("spatial_coverage", None)
        self.tag = kwargs.pop("tag", None) or []
        self.observation_level = kwargs.pop("observation_level", None) or []
        self.locale = kwargs.pop("locale", "pt")
        super().__init__(*args, **kwargs)

    def search(self):
        if not self.is_valid():
            return self.no_query_found()

        # Start with all results
        sqs = self.searchqueryset.all()

        # Text search if provided
        if q := self.cleaned_data.get("q"):
            sqs = (
                sqs.auto_query(q)
                .filter_and(**{"text.edgengram": q})
                .filter_or(**{f"text.snowball_{self.locale}": q})
            )

        # Contains filters
        for qp_value in self.contains:
            sqs = sqs.narrow(f'contains_{qp_value}:"true"')

        # Regular filters
        for qp_key, facet_key in [
            ("tag", "tag_slug"),
            ("theme", "theme_slug"),
            ("observation_level", "entity_slug"),
            ("organization", "organization_slug"),
        ]:
            for qp_value in getattr(self, qp_key, []):
                sqs = sqs.narrow(f'{facet_key}:"{sqs.query.clean(qp_value)}"')

        if self.spatial_coverage:
            # Build queries for all coverage values
            coverage_queries = []
            for coverage_list in self.spatial_coverage:
                # Split the comma-separated values
                coverages = coverage_list.split(",")
                if "world" in coverages:
                    # If world is in the list, only look for world coverage
                    coverage_queries = ['spatial_coverage_exact:"world"']
                    break
                else:
                    # Regular case: handle hierarchical patterns for each coverage
                    for coverage in coverages:
                        parts = coverage.split("_")
                        coverage_patterns = ["_".join(parts[:i]) for i in range(1, len(parts))]
                        coverage_patterns.append(coverage)  # Add the full coverage too

                        # Build OR condition for all valid levels, including world
                        patterns = " OR ".join(
                            f'spatial_coverage_exact:"{pattern}"'
                            for pattern in coverage_patterns + ["world"]
                        )
                        coverage_queries.append(f"({patterns})")

            # Combine all coverage queries with AND
            query = f"_exists_:spatial_coverage_exact AND {' AND '.join(coverage_queries)}"
            sqs = sqs.raw_search(query)

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
        "contains_direct_download_free",
        "contains_direct_download_paid",
        "contains_temporalcoverage_free",
        "contains_temporalcoverage_paid",
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
        return self.request.GET.get("locale", "pt")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"contains": self.request.GET.getlist("contains")})
        kwargs.update({"theme": self.request.GET.getlist("theme")})
        kwargs.update({"organization": self.request.GET.getlist("organization")})
        kwargs.update({"spatial_coverage": self.request.GET.getlist("spatial_coverage")})
        kwargs.update({"tag": self.request.GET.getlist("tag")})
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

    def get_facets(self, sqs: SearchQuerySet, facet_size: int = 6):
        sqs = sqs.facet("theme_slug", size=facet_size)
        sqs = sqs.facet("organization_slug", size=facet_size)
        # sqs = sqs.facet("spatial_coverage", size=facet_size)
        sqs = sqs.facet("tag_slug", size=facet_size)
        sqs = sqs.facet("entity_slug", size=facet_size)

        facets = {}
        facet_counts = sqs.facet_counts()
        facet_counts = facet_counts.get("fields", {}).items()
        for key, values in facet_counts:
            facets[key] = []
            for value in values:
                if not value[0]:
                    continue
                facets[key].append(
                    {
                        "key": value[0],
                        "count": value[1],
                    }
                )

        for key_back, key_front, model in [
            ("theme_slug", "themes", Theme),
            ("organization_slug", "organizations", Organization),
            ("tag_slug", "tags", Tag),
            ("entity_slug", "observation_levels", Entity),
        ]:
            to_name = model.objects.values("slug", f"name_{self.locale}", "name")
            to_name = {
                e["slug"]: {
                    "name": e[f"name_{self.locale}"] or e["name"] or e["slug"],
                    "fallback": e[f"name_{self.locale}"] is None,
                }
                for e in to_name.all()
            }
            facets[key_front] = facets.pop(key_back, None)
            for field in facets[key_front] or []:
                translated_name = to_name.get(field["key"], {})
                field["name"] = translated_name.get("name", field["key"])
                field["fallback"] = translated_name.get("fallback", True)

        # Special handling for spatial coverage
        if "spatial_coverage" in facets:
            spatial_coverages = []
            coverage_counts = {}  # Dictionary to track counts per slug
            coverage_data = {}  # Dictionary to store the full data per slug

            for field in facets.pop("spatial_coverage") or []:
                coverage = field["key"]
                areas = Area.objects.filter(slug=coverage, administrative_level=0)

                if coverage == "world":
                    field["name"] = "World"
                    field["fallback"] = False

                    # Add all top-level areas (administrative_level = 0)
                    top_level_areas = Area.objects.filter(administrative_level=0)
                    for child_area in top_level_areas:
                        slug = child_area.slug
                        coverage_counts[slug] = coverage_counts.get(slug, 0) + field["count"]
                        coverage_data[slug] = {
                            "key": slug,
                            "name": getattr(child_area, f"name_{self.locale}")
                            or child_area.name
                            or slug,
                            "fallback": getattr(child_area, f"name_{self.locale}") is None,
                        }
                elif areas.exists():
                    for area in areas:
                        slug = area.slug
                        coverage_counts[slug] = coverage_counts.get(slug, 0) + field["count"]
                        coverage_data[slug] = {
                            "key": slug,
                            "name": getattr(area, f"name_{self.locale}") or area.name or coverage,
                            "fallback": getattr(area, f"name_{self.locale}") is None,
                        }

            # Create final list with collapsed counts and sort by count
            spatial_coverages = []
            for slug, count in coverage_counts.items():
                entry = coverage_data[slug].copy()
                entry["count"] = count
                spatial_coverages.append(entry)

            # Sort by count in descending order
            spatial_coverages.sort(key=lambda x: x["count"], reverse=True)

            facets["spatial_coverages"] = spatial_coverages

        return facets

    def get_results(self, sqs: SearchQuerySet):
        # Sort and paginate at Elasticsearch level
        sqs = sqs.order_by("-contains_tables", "-_score", "-updated_at")

        start = (self.page - 1) * self.page_size
        end = start + self.page_size
        results = list(sqs[start:end])

        # Pre-fetch all Area objects and cache spatial coverage translations
        all_coverage_slugs = set()
        for r in results:
            if hasattr(r, "spatial_coverage") and r.spatial_coverage:
                all_coverage_slugs.update(r.spatial_coverage)

        spatial_coverage_translations = {}
        if all_coverage_slugs:
            areas = Area.objects.filter(slug__in=all_coverage_slugs).values(
                "slug",
                "name",
                f"name_{self.locale}",
            )

            spatial_coverage_translations = {
                area["slug"]: area[f"name_{self.locale}"] or area["name"] or area["slug"]
                for area in areas
            }

        return [as_search_result(r, self.locale, spatial_coverage_translations) for r in results]


def as_search_result(
    result: SearchResult, locale: str = "pt", spatial_coverage_translations: dict[str, str] = {}
):
    themes = []
    for slug, name in zip(result.theme_slug or [], getattr(result, f"theme_name_{locale}") or []):
        themes.append(
            {
                "slug": slug,
                "name": name,
            }
        )

    organizations = []
    for pk, slug, name, picture in zip(
        result.organization_id or [],
        result.organization_slug or [],
        getattr(result, f"organization_name_{locale}")
        or result.organization_name
        or result.organization_slug
        or [],
        result.organization_picture or [],
    ):
        picture = storage.url(picture) if picture else None
        organizations.append(
            {
                "id": pk,
                "slug": slug,
                "name": name,
                "picture": picture,
            }
        )

    tags = []
    for slug, name in zip(result.tag_slug or [], getattr(result, f"tag_name_{locale}") or []):
        tags.append(
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

    # Add spatial coverage translations using pre-fetched cache
    spatial_coverages = []
    for coverage_slug in result.spatial_coverage or []:
        name = spatial_coverage_translations.get(coverage_slug, coverage_slug)
        spatial_coverages.append({"slug": coverage_slug, "name": name})

    return {
        "updated_at": result.updated_at,
        "id": result.dataset_id,
        "slug": result.dataset_slug,
        "name": getattr(result, f"dataset_name_{locale}")
        or result.dataset_name
        or result.dataset_slug,
        "description": getattr(result, f"dataset_description_{locale}")
        or result.dataset_description,
        "tags": tags,
        "themes": themes,
        "entities": entities,
        "organizations": organizations,
        "temporal_coverage": result.temporal_coverage,
        "spatial_coverage": spatial_coverages,
        "contains_open_data": result.contains_open_data,
        "contains_closed_data": result.contains_closed_data,
        "contains_tables": result.contains_tables,
        "contains_direct_download_free": result.contains_direct_download_free,
        "contains_direct_download_paid": result.contains_direct_download_paid,
        "contains_temporalcoverage_free": result.contains_temporalcoverage_free,
        "contains_temporalcoverage_paid": result.contains_temporalcoverage_paid,
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


class DatasetFacetValuesView(View):
    """
    View para retornar os valores de uma faceta específica baseada nos parâmetros de filtro atuais.
    """

    facet_fields = [
        "tag_slug",
        "theme_slug",
        "entity_slug",
        "organization_slug",
        "spatial_coverage",
    ]

    @property
    def locale(self):
        return self.request.GET.get("locale", "pt")

    @property
    def facet_name(self):
        return self.request.GET.get("facet", "").lower()

    def get_form_kwargs(self):
        kwargs = {
            "contains": self.request.GET.getlist("contains"),
            "theme": self.request.GET.getlist("theme"),
            "organization": self.request.GET.getlist("organization"),
            "spatial_coverage": self.request.GET.getlist("spatial_coverage"),
            "tag": self.request.GET.getlist("tag"),
            "observation_level": self.request.GET.getlist("observation_level"),
            "locale": self.locale,
        }

        if "q" in self.request.GET:
            kwargs["data"] = {"q": self.request.GET["q"]}

        return kwargs

    def get(self, request, *args, **kwargs):
        if self.facet_name not in self.facet_fields:
            return JsonResponse(
                {
                    "error": f"Facet '{self.facet_name}' not available. Choose from: {self.facet_fields}"  # noqa: E501
                },
                status=400,
            )

        form = DatasetSearchForm(**self.get_form_kwargs())
        sqs = form.search()

        sqs = sqs.facet(self.facet_name, size=1000)  # Tamanho grande para pegar todos os valores

        facet_counts = sqs.facet_counts()
        facet_values = facet_counts.get("fields", {}).get(self.facet_name, [])

        values = [{"key": value[0], "count": value[1]} for value in facet_values if value[0]]

        if self.facet_name == "theme_slug":
            model = Theme
            name_field = f"name_{self.locale}"
        elif self.facet_name == "organization_slug":
            model = Organization
            name_field = f"name_{self.locale}"
        elif self.facet_name == "tag_slug":
            model = Tag
            name_field = f"name_{self.locale}"
        elif self.facet_name == "entity_slug":
            model = Entity
            name_field = f"name_{self.locale}"
        elif self.facet_name == "spatial_coverage":
            model = Area
            name_field = f"name_{self.locale}"
        else:
            model = None

        if model:
            slugs = [v["key"] for v in values]
            translated_names = model.objects.filter(slug__in=slugs).values(
                "slug", name_field, "name"
            )
            name_map = {
                item["slug"]: {
                    "name": item.get(name_field) or item.get("name") or item["slug"],
                    "fallback": name_field not in item or item[name_field] is None,
                }
                for item in translated_names
            }

            for value in values:
                translated = name_map.get(value["key"], {"name": value["key"], "fallback": True})
                value.update(translated)

        return JsonResponse(
            {
                "facet": self.facet_name,
                "values": values,
                "count": len(values),
                "locale": self.locale,
            }
        )
