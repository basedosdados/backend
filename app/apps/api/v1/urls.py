# -*- coding: utf-8 -*-
from django.http import HttpResponseRedirect
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from graphene_file_upload.django import FileUploadGraphQLView


def redirect_to_v1(request):
    return HttpResponseRedirect("/api/v1/")


def redirect_to_v1_graphql(request):
    return HttpResponseRedirect("/api/v1/graphql")


urlpatterns = [
    path("", redirect_to_v1),
    path("v1/", redirect_to_v1_graphql),
    path(
        "v1/graphql",
        csrf_exempt(FileUploadGraphQLView.as_view(graphiql=True)),
    ),
]
