# -*- coding: utf-8 -*-
from django.urls import path
from basedosdados_api.core.views import (
    HomeView,
)

urlpatterns = [
    path("", HomeView.as_view()),
]
