# -*- coding: utf-8 -*-
"""app URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic.base import TemplateView

from app.apps.api.v1.views import DatasetESSearchView


def render_robots():
    return TemplateView.as_view(template_name="robots.txt", content_type="text/plain")


urlpatterns = [
    # Meta
    path("robots.txt", render_robots()),
    re_path(r"^healthcheck/", include("health_check.urls")),
    # Admin
    path("admin/", admin.site.urls),
    # Applications
    path("", include("app.apps.core.urls")),
    path("account/", include("app.apps.account.urls")),
    path("api/", include("app.apps.api.v1.urls")),
    path("schemas/", include("app.apps.schemas.urls")),
    path("search/", DatasetESSearchView.as_view()),
    path("search/debug/", include("haystack.urls")),
    path("payments/", include("app.apps.payments.urls")),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
