# -*- coding: utf-8 -*-
from django.urls import include, path

urlpatterns = [path("payment/", include("djstripe.urls", namespace="payment"))]
