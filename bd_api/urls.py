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

from bd_api.apps.api.v1.views import DatasetESSearchView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("bd_api.apps.core.urls")),
    path("api/", include("bd_api.apps.api.v1.urls")),
    path("account/", include("bd_api.apps.account.urls")),
    path("search/", DatasetESSearchView.as_view()),
    path("search/debug/", include("haystack.urls")),
    path("payment/", include("bd_api.apps.payment.urls")),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
