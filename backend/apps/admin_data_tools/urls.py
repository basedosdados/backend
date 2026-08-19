# -*- coding: utf-8 -*-
from django.urls import path

from .views import FlowFailedWebhookView, SetScheduleActiveView, SyncDeploymentsView

urlpatterns = [
    path("admin-tools/sync-deployments/", SyncDeploymentsView.as_view(), name="sync-deployments"),
    path("admin-tools/flow-failed/", FlowFailedWebhookView.as_view(), name="flow-failed"),
    path(
        "admin-tools/set-schedule-active/",
        SetScheduleActiveView.as_view(),
        name="set-schedule-active",
    ),
]
