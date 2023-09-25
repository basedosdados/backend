# -*- coding: utf-8 -*-
from django.urls import path

from basedosdados_api.core.views import (
    DatasetCreateView,
    DatasetDeleteView,
    DatasetRedirectView,
    DatasetUpdateView,
    HomeView,
)

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("dataset/", DatasetCreateView.as_view(), name="dataset"),
    path("dataset_redirect/", DatasetRedirectView.as_view(), name="dataset_redirect"),
    path("dataset/<uuid:pk>/", DatasetUpdateView.as_view(), name="dataset-detail"),
    path("dataset/<uuid:pk>/delete/", DatasetDeleteView.as_view(), name="datasetdelete"),
]
