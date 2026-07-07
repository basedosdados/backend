# -*- coding: utf-8 -*-
from django.urls import path

from .views import FlowFailedWebhookView, SyncDeploymentsView

urlpatterns = [
    path("admin-tools/sync-deployments/", SyncDeploymentsView.as_view(), name="sync-deployments"),
    path("admin-tools/flow-failed/", FlowFailedWebhookView.as_view(), name="flow-failed"),
]
