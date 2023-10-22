# -*- coding: utf-8 -*-

import json
from pathlib import Path

from django.http.response import JsonResponse
from django.views import View


class DatasetSchemaView(View):
    def get(self, request):
        with open(Path.cwd().parent / "bd_api/schemas/repository/dataset_schema.json") as f:
            schema = json.load(f)
        return JsonResponse(schema, safe=False)


class TableSchemaView(View):
    def get(self, request):
        with open(Path.cwd().parent / "bd_api/schemas/repository/table_schema.json") as f:
            schema = json.load(f)
        return JsonResponse(schema, safe=False)


class ColumnSchemaView(View):
    def get(self, request):
        with open(Path.cwd().parent / "bd_api/schemas/repository/columns_schema.json") as f:
            schema = json.load(f)
        return JsonResponse(schema, safe=False)


class BdsSpatialCoverageTreeSchemaView(View):
    def get(self, request):
        with open(
            Path.cwd().parent / "bd_api/schemas/repository/bd_spatial_coverage_tree.json"
        ) as f:
            schema = json.load(f)
        return JsonResponse(schema, safe=False)
