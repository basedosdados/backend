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
from django.contrib import admin
from django.urls import include, path, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from basedosdados_api.api.urls import urlpatterns as api_urlpatterns

schema_view = get_schema_view(
    openapi.Info(
        title="Base dos Dados API",
        default_version="v1",
        description="API de gerenciamento de metadados da Base dos Dados",
        terms_of_service="",
        contact=openapi.Contact(email="contato@basedosdados.org"),
        license=openapi.License(name="GPLv3"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path("admin/", admin.site.urls),
    re_path(r"^healthcheck/", include("health_check.urls")),
    path("api/", include(api_urlpatterns)),
    path("api/account/", include("basedosdados_api.account.urls")),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path(
        "docs/",
        schema_view.with_ui("swagger", cache_timeout=0),
    ),
    re_path(
        r"^docs(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
]
