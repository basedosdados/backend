# -*- coding: utf-8 -*-
from rest_framework import permissions, viewsets

from basedosdados_api.api.v1.models import (
    Organization,
    Dataset,
    Table,
    Column,
    CloudTable,
)
from basedosdados_api.api.v1.serializers import (
    OrganizationSerializer,
    DatasetSerializer,
    TableSerializer,
    ColumnSerializer,
    CloudTableSerializer,
)


class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated]


class DatasetViewSet(viewsets.ModelViewSet):
    serializer_class = DatasetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Dataset.objects.all()
        organization = self.request.query_params.get("organization", None)
        if organization is not None:
            queryset = queryset.filter(organization__id=organization)
        return queryset


class TableViewSet(viewsets.ModelViewSet):
    serializer_class = TableSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Table.objects.all()
        dataset = self.request.query_params.get("dataset", None)
        organization = self.request.query_params.get("organization", None)
        if dataset is not None:
            queryset = queryset.filter(dataset__id=dataset)
        if organization is not None:
            queryset = queryset.filter(dataset__organization__id=organization)
        return queryset


class ColumnViewSet(viewsets.ModelViewSet):
    serializer_class = ColumnSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Column.objects.all()
        table = self.request.query_params.get("table", None)
        dataset = self.request.query_params.get("dataset", None)
        organization = self.request.query_params.get("organization", None)
        if table is not None:
            queryset = queryset.filter(table__id=table)
        if dataset is not None:
            queryset = queryset.filter(table__dataset__id=dataset)
        if organization is not None:
            queryset = queryset.filter(table__dataset__organization__id=organization)
        return queryset


class CloudTableViewSet(viewsets.ModelViewSet):
    serializer_class = CloudTableSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = CloudTable.objects.all()
        # table = self.request.query_params.get("table", None)
        # dataset = self.request.query_params.get("dataset", None)
        # organization = self.request.query_params.get("organization", None)
        # if table is not None:
        #     queryset = queryset.filter(table__id=table)
        # if dataset is not None:
        #     queryset = queryset.filter(table__dataset__id=dataset)
        # if organization is not None:
        #     queryset = queryset.filter(table__dataset__organization__id=organization)
        return queryset
