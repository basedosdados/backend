# -*- coding: utf-8 -*-
from django.urls import path
from basedosdados_api.core.views import (
    HomeView,
    DatasetView
)

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("dataset/<uuid:id>/", DatasetView.as_view()),
]
