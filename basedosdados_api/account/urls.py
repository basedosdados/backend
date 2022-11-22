# -*- coding: utf-8 -*-
from django.urls import path
from basedosdados_api.account.views import LoadUserView, RegisterView

urlpatterns = [
    path("user", LoadUserView.as_view(), name="user"),
    path("register", RegisterView.as_view(), name="register"),
]
