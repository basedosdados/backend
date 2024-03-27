# -*- coding: utf-8 -*-
from django.urls import path

from . import views

urlpatterns = [
    path("", views.auth, name="auth"),
    path("login/", views.signin, name="login"),
    path("logout/", views.signout, name="logout"),
]
