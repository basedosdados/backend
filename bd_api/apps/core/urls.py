# -*- coding: utf-8 -*-
from django.urls import include, path, re_path
from django.views.generic import RedirectView, TemplateView

from bd_api.apps.core.views import (
    DatasetCreateView,
    DatasetDeleteView,
    DatasetRedirectView,
    DatasetUpdateView,
)


def render_robots():
    return TemplateView.as_view(template_name="robots.txt", content_type="text/plain")


urlpatterns = [
    path("robots.txt", render_robots()),
    re_path(r"^healthcheck/", include("health_check.urls")),
    path("", RedirectView.as_view(url="admin", permanent=True), name="home"),
    #
    path("dataset/", DatasetCreateView.as_view(), name="dataset"),
    path("dataset_redirect/", DatasetRedirectView.as_view(), name="dataset_redirect"),
    path("dataset/<uuid:pk>/", DatasetUpdateView.as_view(), name="dataset_detail"),
    path("dataset/<uuid:pk>/delete/", DatasetDeleteView.as_view(), name="dataset_delete"),
]
