# -*- coding: utf-8 -*-
from django.urls import path

from bd_api.apps.schemas.views import (
    BdsSpatialCoverageTreeSchemaView,
    ColumnSchemaView,
    DatasetSchemaView,
    TableSchemaView,
)

urlpatterns = [
    path("bd_dataset_schema/", DatasetSchemaView.as_view()),
    path("bd_bdm_table_schema/", TableSchemaView.as_view()),
    path("bd_bdm_columns_schema/", ColumnSchemaView.as_view()),
    path("bd_spatial_coverage_tree/", BdsSpatialCoverageTreeSchemaView.as_view()),
]
