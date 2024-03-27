# -*- coding: utf-8 -*-
"""bd_api URL Configuration

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
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt
from graphene_file_upload.django import FileUploadGraphQLView

from bd_api.apps.api.v1.search_views import DatasetSearchView as DatasetSearchV2View
from bd_api.apps.api.v1.views import DatasetRedirectView
from bd_api.apps.api.v1.views import DatasetSearchView as DatasetSearchV1View


def graphql_view():
    return csrf_exempt(FileUploadGraphQLView.as_view(graphiql=True))


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("bd_api.apps.core.urls")),
    path("api/", include("bd_api.apps.api.v1.urls")),
    path("api/graphql/", graphql_view()),
    path("account/", include("bd_api.apps.account.urls")),
    path("auth/", include("bd_api.apps.account_auth.urls")),
    path("search/", DatasetSearchV1View.as_view()),
    path("search/v2/", DatasetSearchV2View.as_view()),
    path("search/debug/", include("haystack.urls")),
    path("dataset/", DatasetRedirectView.as_view()),
    path("dataset_redirect/", DatasetRedirectView.as_view()),
    path("payment/", include("bd_api.apps.account_payment.urls")),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
