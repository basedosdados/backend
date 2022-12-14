# -*- coding: utf-8 -*-
from rest_framework import serializers

from basedosdados_api.api.v1.models import (
    Organization,
    Dataset,
    Table,
    BigQueryTypes,
    Column,
    CloudTable,
)


class OrganizationPublicSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "slug", "name_en", "name_pt", "website"]


class OrganizationSerializer(OrganizationPublicSerializer):
    pass


class DatasetPublicSerializer(serializers.HyperlinkedModelSerializer):

    organization = serializers.HyperlinkedRelatedField(
        view_name="organization-public-detail", queryset=Organization.objects.all()
    )

    class Meta:
        model = Dataset
        fields = ["id", "organization", "slug", "name_en", "name_pt"]


class DatasetSerializer(DatasetPublicSerializer):
    organization = serializers.HyperlinkedRelatedField(
        view_name="organization-private-detail", queryset=Organization.objects.all()
    )


class TablePublicSerializer(serializers.HyperlinkedModelSerializer):

    dataset = serializers.HyperlinkedRelatedField(
        view_name="dataset-public-detail", queryset=Dataset.objects.all()
    )
    cloud_tables = serializers.HyperlinkedRelatedField(
        view_name="cloudtable-public-detail",
        queryset=CloudTable.objects.all(),
        many=True,
    )

    class Meta:
        model = Table
        fields = [
            "id",
            "dataset",
            "cloud_tables",
            "slug",
            "name_en",
            "name_pt",
            "description",
            "is_directory",
            "data_cleaned_description",
            "data_cleaned_code_url",
            "raw_data_url",
            "auxiliary_files_url",
            "architecture_url",
            "source_bucket_name",
            "uncompressed_file_size",
            "compressed_file_size",
            "number_of_rows",
        ]


class TableSerializer(TablePublicSerializer):
    dataset = serializers.HyperlinkedRelatedField(
        view_name="dataset-private-detail", queryset=Dataset.objects.all()
    )
    cloud_tables = serializers.HyperlinkedRelatedField(
        view_name="cloudtable-private-detail",
        queryset=CloudTable.objects.all(),
        many=True,
    )


class BigQueryTypesPublicSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = BigQueryTypes
        fields = ["id", "name"]


class BigQueryTypesSerializer(BigQueryTypesPublicSerializer):
    pass


class ColumnPublicSerializer(serializers.HyperlinkedModelSerializer):

    table = serializers.HyperlinkedRelatedField(
        view_name="table-public-detail", queryset=Table.objects.all()
    )
    bigquery_type = serializers.HyperlinkedRelatedField(
        view_name="bigquerytypes-public-detail", queryset=BigQueryTypes.objects.all()
    )

    class Meta:
        model = Column
        fields = [
            "id",
            "table",
            "bigquery_type",
            "slug",
            "name_en",
            "name_pt",
            "is_in_staging",
            "is_partition",
            "description",
            "coverage_by_dictionary",
            "measurement_unit",
            "has_sensitive_data",
            "observations",
        ]


class ColumnSerializer(ColumnPublicSerializer):
    table = serializers.HyperlinkedRelatedField(
        view_name="table-private-detail", queryset=Table.objects.all()
    )
    bigquery_type = serializers.HyperlinkedRelatedField(
        view_name="bigquerytypes-private-detail", queryset=BigQueryTypes.objects.all()
    )


class CloudTablePublicSerializer(serializers.HyperlinkedModelSerializer):
    tables = serializers.HyperlinkedRelatedField(
        view_name="table-public-detail", queryset=Table.objects.all(), many=True
    )

    class Meta:
        model = CloudTable
        fields = ["tables", "gcp_project_id", "gcp_dataset_id", "gcp_table_id"]


class CloudTableSerializer(CloudTablePublicSerializer):
    tables = serializers.HyperlinkedRelatedField(
        view_name="table-private-detail", queryset=Table.objects.all(), many=True
    )
