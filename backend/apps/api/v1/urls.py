# -*- coding: utf-8 -*-
from django.http import HttpResponseRedirect
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from graphene_file_upload.django import FileUploadGraphQLView

from backend.apps.api.v1.search_views import DatasetFacetValuesView, DatasetSearchView
from backend.apps.api.v1.views import (
    DatasetRedirectView,
    columns_view,
    table_stats,
    upload_columns,
)
from backend.apps.api.v1.views_export import ExportTablesView


def redirect_to_graphql(request):
    return HttpResponseRedirect("graphql")


def graphql_view():
    return csrf_exempt(FileUploadGraphQLView.as_view(graphiql=True))


urlpatterns = [
    path("api/", redirect_to_graphql),
    path("api/v1/", redirect_to_graphql),
    path("api/v1/graphql", graphql_view()),
    path("graphql", graphql_view()),
    path("search/", DatasetSearchView.as_view()),
    path("facet_values/", DatasetFacetValuesView.as_view()),
    path("dataset/", DatasetRedirectView.as_view()),
    path("dataset_redirect/", DatasetRedirectView.as_view()),
    path("tables/stats/", table_stats),
    path("upload_columns/", upload_columns),
    path("columns/", columns_view),
    path("tables/<uuid:table_id>/columns/", columns_view),
    path("columns/<uuid:column_id>/", columns_view),
    path("export/catalog/", ExportTablesView.as_view(), name="export-catalog"),
]
