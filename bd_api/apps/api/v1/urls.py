# -*- coding: utf-8 -*-
from django.http import HttpResponseRedirect
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt
from graphene_file_upload.django import FileUploadGraphQLView

from bd_api.apps.api.v1.search_views import DatasetSearchView
from bd_api.apps.api.v1.views import DatasetRedirectView


def redirect_to_v1(request):
    return HttpResponseRedirect("/api/v1/graphql")


def graphql_view():
    return csrf_exempt(FileUploadGraphQLView.as_view(graphiql=True))


urlpatterns = [
    path("api/", redirect_to_v1),
    path("api/v1/", redirect_to_v1),
    path("api/v1/graphql", graphql_view()),
    path("search/", DatasetSearchView.as_view()),
    path("search/debug/", include("haystack.urls")),
    path("dataset/", DatasetRedirectView.as_view()),
    path("dataset_redirect/", DatasetRedirectView.as_view()),
]
