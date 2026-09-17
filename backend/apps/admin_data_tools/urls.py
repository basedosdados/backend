# -*- coding: utf-8 -*-
from django.urls import path

from .bigquery_sync import CheckMetadadosView, SyncUpdateLatestView
from .column_import import UploadColumnsView
from .flow_monitoring import FlowFailedWebhookView, SyncDeploymentsView

urlpatterns = [
    path("admin-tools/sync-deployments/", SyncDeploymentsView.as_view(), name="sync-deployments"),
    path("admin-tools/flow-failed/", FlowFailedWebhookView.as_view(), name="flow-failed"),
    path("admin-tools/check-metadados/", CheckMetadadosView.as_view(), name="check-metadados"),
    path(
        "admin-tools/sync-update-latest/",
        SyncUpdateLatestView.as_view(),
        name="sync-update-latest",
    ),
    path("admin-tools/upload-columns/", UploadColumnsView.as_view(), name="upload-columns"),
]
