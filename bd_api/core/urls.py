# -*- coding: utf-8 -*-
from django.urls import path
from django.views.generic import RedirectView

from bd_api.core.views import (
    DatasetCreateView,
    DatasetDeleteView,
    DatasetRedirectView,
    DatasetUpdateView,
)

urlpatterns = [
    path("", RedirectView.as_view(url="admin", permanent=True)),
    path("dataset/", DatasetCreateView.as_view(), name="dataset"),
    path("dataset_redirect/", DatasetRedirectView.as_view(), name="dataset_redirect"),
    path("dataset/<uuid:pk>/", DatasetUpdateView.as_view(), name="dataset-detail"),
    path("dataset/<uuid:pk>/delete/", DatasetDeleteView.as_view(), name="datasetdelete"),
]
