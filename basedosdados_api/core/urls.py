# -*- coding: utf-8 -*-
from django.urls import path
from basedosdados_api.core.views import (
    HomeView,
    DatasetCreateView,
    DatasetUpdateView,
    DatasetDeleteView,
)

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("dataset/", DatasetCreateView.as_view(), name="dataset"),
    path("dataset/<uuid:pk>/", DatasetUpdateView.as_view(), name="dataset-detail"),
    path("dataset/<uuid:pk>/delete/", DatasetDeleteView.as_view(), name="datasetdelete"),
]
