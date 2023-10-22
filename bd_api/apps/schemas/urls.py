# -*- coding: utf-8 -*-
from django.urls import path

from bd_api.apps.schemas.views import ColumnSchemaView, DatasetSchemaView, TableSchemaView

urlpatterns = [
    path("bd_dataset_schema/", DatasetSchemaView.as_view()),
    path("bd_bdm_table_schema/", TableSchemaView.as_view()),
    path("bd_bdm_columns_schema/", ColumnSchemaView.as_view()),
]
