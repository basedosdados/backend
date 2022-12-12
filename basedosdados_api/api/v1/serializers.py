# -*- coding: utf-8 -*-
from rest_framework import serializers

from basedosdados_api.api.v1.models import (
    Organization,
    Dataset,
    Table,
    Column,
    CloudTable,
)


class OrganizationSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Organization
        fields = ["id"]


class DatasetSerializer(serializers.HyperlinkedModelSerializer):

    organization = serializers.HyperlinkedRelatedField(
        view_name="organization-detail", queryset=Organization.objects.all()
    )

    class Meta:
        model = Dataset
        fields = ["id", "organization"]


class TableSerializer(serializers.HyperlinkedModelSerializer):

    dataset = serializers.HyperlinkedRelatedField(
        view_name="dataset-detail", queryset=Dataset.objects.all()
    )

    class Meta:
        model = Table
        fields = ["id", "dataset"]


class ColumnSerializer(serializers.HyperlinkedModelSerializer):

    table = serializers.HyperlinkedRelatedField(
        view_name="table-detail", queryset=Table.objects.all()
    )

    class Meta:
        model = Column
        fields = ["id", "table"]


class CloudTableSerializer(serializers.HyperlinkedModelSerializer):
    table = serializers.HyperlinkedRelatedField(
        view_name="table-detail", queryset=Table.objects.all()
    )

    class Meta:
        model = CloudTable
        fields = ["table", "gcp_project_id", "gcp_dataset_id", "gcp_table_id"]
