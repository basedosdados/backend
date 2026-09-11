# -*- coding: utf-8 -*-
from django.urls import path

from .views import (
    DataAPICreditAddView,
    DataAPICreditDeductView,
    DataAPICurrentTierView,
    DataAPIEndpointValidateView,
    DataAPIKeyValidateView,
    DataAPIRequestRegisterView,
)

urlpatterns = [
    path(
        "data_api/keys/validate",
        DataAPIKeyValidateView.as_view(),
        name="validate_api_key",
    ),
    path(
        "data_api/credits/add",
        DataAPICreditAddView.as_view(),
        name="add_credit",
    ),
    path(
        "data_api/credits/deduct",
        DataAPICreditDeductView.as_view(),
        name="deduct_credit",
    ),
    path(
        "data_api/endpoints/validate",
        DataAPIEndpointValidateView.as_view(),
        name="validate_endpoint",
    ),
    path(
        "data_api/requests/current_tier",
        DataAPICurrentTierView.as_view(),
        name="current_tier",
    ),
    path(
        "data_api/requests/register",
        DataAPIRequestRegisterView.as_view(),
        name="register_request",
    ),
]
