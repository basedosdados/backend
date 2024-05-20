# -*- coding: utf-8 -*-
from django.urls import path

from backend.apps.account.views import (
    AccountActivateConfirmView,
    AccountActivateView,
    PasswordResetConfirmView,
    PasswordResetView,
)

urlpatterns = [
    path(
        "account/account_activate/<uidb64>/",
        AccountActivateView.as_view(),
        name="activate",
    ),
    path(
        "account/account_activate_confirm/<uidb64>/<token>/",
        AccountActivateConfirmView.as_view(),
        name="activate",
    ),
    path(
        "account/password_reset/<uidb64>/",
        PasswordResetView.as_view(),
        name="password_reset",
    ),
    path(
        "account/password_reset_confirm/<uidb64>/<token>/",
        PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
]
