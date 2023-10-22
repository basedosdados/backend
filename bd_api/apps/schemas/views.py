# -*- coding: utf-8 -*-

from json import loads
from pathlib import Path

from django.http.response import JsonResponse
from django.views import View


def load(filename: str) -> dict:
    filepath = Path(__file__).parent / "repository" / f"{filename}.json"
    return loads(filepath.read_text())


class DatasetSchemaView(View):
    def get(self, request):
        schema = load("dataset_schema")
        return JsonResponse(schema, safe=False)


class TableSchemaView(View):
    def get(self, request):
        schema = load("table_schema")
        return JsonResponse(schema, safe=False)


class ColumnSchemaView(View):
    def get(self, request):
        schema = load("columns_schema")
        return JsonResponse(schema, safe=False)
