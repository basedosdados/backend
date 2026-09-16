# -*- coding: utf-8 -*-
from django.urls import path

from .views import (
    CheckMetadadosView,
    FlowFailedWebhookView,
    SetScheduleActiveView,
    SyncDeploymentsView,
    SyncUpdateLatestView,
)

urlpatterns = [
    path("admin-tools/sync-deployments/", SyncDeploymentsView.as_view(), name="sync-deployments"),
    path("admin-tools/flow-failed/", FlowFailedWebhookView.as_view(), name="flow-failed"),
    path("admin-tools/check-metadados/", CheckMetadadosView.as_view(), name="check-metadados"),
    path(
        "admin-tools/sync-update-latest/",
        SyncUpdateLatestView.as_view(),
        name="sync-update-latest",
    ),
    path(
        "admin-tools/set-schedule-active/",
        SetScheduleActiveView.as_view(),
        name="set-schedule-active",
    ),
]
