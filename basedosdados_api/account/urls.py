# -*- coding: utf-8 -*-
from django.urls import path
from basedosdados_api.account.views import (
    LoadUserView,
    RegisterView,
    PasswordResetView,
    LoginView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetCompleteView, ActivateAccount,
)

urlpatterns = [
    # path("user", LoadUserView.as_view(), name="user"),
    path("activate/<uidb64>/<token>/", ActivateAccount.as_view(), name="activate"),
    path("register", RegisterView.as_view(), name="account-register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("password_reset", PasswordResetView.as_view(), name="password_reset"),
    path("password_reset_confirv/<uidb64>/<token>/", PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("password_reset_done", PasswordResetCompleteView.as_view(), name="password_reset_complete"),
]
