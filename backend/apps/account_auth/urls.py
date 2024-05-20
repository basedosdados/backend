# -*- coding: utf-8 -*-
from django.urls import path

from . import views

urlpatterns = [
    path("auth/", views.auth, name="auth"),
    path("auth/login/", views.signin, name="login"),
    path("auth/logout/", views.signout, name="logout"),
]
