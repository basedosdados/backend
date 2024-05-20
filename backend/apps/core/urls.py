# -*- coding: utf-8 -*-
from django.urls import include, path, re_path
from django.views.generic import RedirectView, TemplateView


def render_robots():
    return TemplateView.as_view(template_name="robots.txt", content_type="text/plain")


urlpatterns = [
    path("robots.txt", render_robots()),
    re_path(r"^healthcheck/", include("health_check.urls")),
    path("", RedirectView.as_view(url="admin", permanent=True), name="home"),
]
