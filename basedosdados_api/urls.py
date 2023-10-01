# -*- coding: utf-8 -*-
"""basedosdados_api URL Configuration

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
from django.http import HttpResponseRedirect
from django.urls import include, path, re_path
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import TemplateView
from graphene_file_upload.django import FileUploadGraphQLView

from basedosdados_api.api.v1.views import DatasetESSearchView


def redirect_to_v1(request):
    return HttpResponseRedirect("/api/v1/")


def redirect_to_v1_graphql(request):
    return HttpResponseRedirect("/api/v1/graphql")


def render_robots():
    return TemplateView.as_view(template_name="robots.txt", content_type="text/plain")


urlpatterns = [
    re_path(r"^healthcheck/", include("health_check.urls")),
    path("admin/", admin.site.urls),
    path("martor/", include("martor.urls")),
    path("account/", include("basedosdados_api.account.urls")),
    path("api/", redirect_to_v1, name="api"),
    path("api/v1/", redirect_to_v1_graphql),
    path(
        "api/v1/graphql",
        csrf_exempt(FileUploadGraphQLView.as_view(graphiql=True)),
    ),
    path("schemas/", include("basedosdados_api.schemas.urls")),
    path("", include("basedosdados_api.core.urls")),
    path("search/", DatasetESSearchView.as_view()),
    path("search/debug/", include("haystack.urls")),
    path("robots.txt", render_robots()),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
