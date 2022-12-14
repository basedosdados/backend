# -*- coding: utf-8 -*-
from rest_framework import serializers

from basedosdados_api.api.v1.models import (
    Organization,
    Dataset,
    Table,
    Column,
    CloudTable,
)


class OrganizationPublicSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Organization
        fields = ["id"]


class OrganizationSerializer(OrganizationPublicSerializer):
    pass


class DatasetPublicSerializer(serializers.HyperlinkedModelSerializer):

    organization = serializers.HyperlinkedRelatedField(
        view_name="organization-public-detail", queryset=Organization.objects.all()
    )

    class Meta:
        model = Dataset
        fields = ["id", "organization"]


class DatasetSerializer(DatasetPublicSerializer):
    organization = serializers.HyperlinkedRelatedField(
        view_name="organization-private-detail", queryset=Organization.objects.all()
    )


class TablePublicSerializer(serializers.HyperlinkedModelSerializer):

    dataset = serializers.HyperlinkedRelatedField(
        view_name="dataset-public-detail", queryset=Dataset.objects.all()
    )

    class Meta:
        model = Table
        fields = ["id", "dataset"]


class TableSerializer(TablePublicSerializer):
    dataset = serializers.HyperlinkedRelatedField(
        view_name="dataset-private-detail", queryset=Dataset.objects.all()
    )


class ColumnPublicSerializer(serializers.HyperlinkedModelSerializer):

    table = serializers.HyperlinkedRelatedField(
        view_name="table-public-detail", queryset=Table.objects.all()
    )

    class Meta:
        model = Column
        fields = ["id", "table"]


class ColumnSerializer(ColumnPublicSerializer):
    table = serializers.HyperlinkedRelatedField(
        view_name="table-private-detail", queryset=Table.objects.all()
    )


class CloudTablePublicSerializer(serializers.HyperlinkedModelSerializer):
    table = serializers.HyperlinkedRelatedField(
        view_name="table-public-detail", queryset=Table.objects.all()
    )

    class Meta:
        model = CloudTable
        fields = ["table", "gcp_project_id", "gcp_dataset_id", "gcp_table_id"]


class CloudTableSerializer(CloudTablePublicSerializer):
    table = serializers.HyperlinkedRelatedField(
        view_name="table-private-detail", queryset=Table.objects.all()
    )
