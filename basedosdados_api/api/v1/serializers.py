# -*- coding: utf-8 -*-
from rest_framework import serializers

from basedosdados_api.api.v1.models import (
    Organization,
    Dataset,
    Table,
    InformationRequest,
    RawDataSource,
    BigQueryTypes,
    Column,
    CloudTable,
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
    cloud_tables = serializers.HyperlinkedRelatedField(
        view_name="cloudtable-public-detail",
        queryset=CloudTable.objects.all(),
        many=True,
    )
    bigquery_type = BigQueryTypesPublicSerializer()

    class Meta:
        model = Column
        fields = [
            "id",
            "table",
            "cloud_tables",
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
    cloud_tables = serializers.HyperlinkedRelatedField(
        view_name="cloudtable-private-detail",
        queryset=CloudTable.objects.all(),
        many=True,
    )
    bigquery_type = BigQueryTypesSerializer()


class ColumnNestedPublicSerializer(ColumnPublicSerializer):
    class Meta:
        model = Column
        fields = [
            "id",
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


class ColumnNestedSerializer(ColumnSerializer):
    class Meta:
        model = Column
        fields = [
            "id",
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


class TablePublicSerializer(serializers.HyperlinkedModelSerializer):

    dataset = serializers.HyperlinkedRelatedField(
        view_name="dataset-public-detail", queryset=Dataset.objects.all()
    )
    cloud_tables = serializers.HyperlinkedRelatedField(
        view_name="cloudtable-public-detail",
        queryset=CloudTable.objects.all(),
        many=True,
    )
    columns = ColumnNestedPublicSerializer(many=True)

    class Meta:
        model = Table
        fields = [
            "id",
            "dataset",
            "cloud_tables",
            "columns",
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
    columns = ColumnNestedSerializer(many=True)


class TableNestedPublicSerializer(TablePublicSerializer):
    class Meta:
        model = Table
        fields = [
            "id",
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


class TableNestedSerializer(TableSerializer):
    class Meta:
        model = Table
        fields = [
            "id",
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


class RawDataSourcePublicSerializer(serializers.HyperlinkedModelSerializer):
    dataset = serializers.HyperlinkedRelatedField(
        view_name="dataset-public-detail", queryset=Dataset.objects.all()
    )

    class Meta:
        model = RawDataSource
        fields = [
            "id",
            "dataset",
            "slug",
            "name_en",
            "name_pt",
            "description",
            "raw_data_url",
            "auxiliary_files_url",
            "architecture_url",
        ]


class RawDataSourceSerializer(RawDataSourcePublicSerializer):
    dataset = serializers.HyperlinkedRelatedField(
        view_name="dataset-private-detail", queryset=Dataset.objects.all()
    )


class RawDataSourceNestedPublicSerializer(RawDataSourcePublicSerializer):
    class Meta:
        model = RawDataSource
        fields = [
            "id",
            "slug",
            "name_en",
            "name_pt",
            "description",
            "raw_data_url",
            "auxiliary_files_url",
            "architecture_url",
        ]


class RawDataSourceNestedSerializer(RawDataSourceSerializer):
    class Meta:
        model = RawDataSource
        fields = [
            "id",
            "slug",
            "name_en",
            "name_pt",
            "description",
            "raw_data_url",
            "auxiliary_files_url",
            "architecture_url",
        ]


class InformationRequestPublicSerializer(serializers.HyperlinkedModelSerializer):
    dataset = serializers.HyperlinkedRelatedField(
        view_name="dataset-public-detail", queryset=Dataset.objects.all()
    )

    class Meta:
        model = InformationRequest
        fields = [
            "id",
            "dataset",
            "slug",
            "name_en",
            "name_pt",
            "description",
            "raw_data_url",
            "auxiliary_files_url",
            "architecture_url",
        ]


class InformationRequestSerializer(InformationRequestPublicSerializer):
    dataset = serializers.HyperlinkedRelatedField(
        view_name="dataset-private-detail", queryset=Dataset.objects.all()
    )


class InformationRequestNestedPublicSerializer(InformationRequestPublicSerializer):
    class Meta:
        model = InformationRequest
        fields = [
            "id",
            "slug",
            "name_en",
            "name_pt",
            "description",
            "raw_data_url",
            "auxiliary_files_url",
            "architecture_url",
        ]


class InformationRequestNestedSerializer(InformationRequestSerializer):
    class Meta:
        model = InformationRequest
        fields = [
            "id",
            "slug",
            "name_en",
            "name_pt",
            "description",
            "raw_data_url",
            "auxiliary_files_url",
            "architecture_url",
        ]


class CloudTablePublicSerializer(serializers.HyperlinkedModelSerializer):
    table = serializers.HyperlinkedRelatedField(
        view_name="table-public-detail", queryset=Table.objects.all()
    )
    columns = ColumnNestedPublicSerializer(many=True)

    class Meta:
        model = CloudTable
        fields = [
            "id",
            "table",
            "columns",
            "gcp_project_id",
            "gcp_dataset_id",
            "gcp_table_id",
        ]


class CloudTableSerializer(CloudTablePublicSerializer):
    table = serializers.HyperlinkedRelatedField(
        view_name="table-private-detail", queryset=Table.objects.all()
    )
    columns = ColumnNestedSerializer(many=True)


class DatasetPublicSerializer(serializers.HyperlinkedModelSerializer):

    organization = serializers.HyperlinkedRelatedField(
        view_name="organization-public-detail", queryset=Organization.objects.all()
    )
    tables = TableNestedPublicSerializer(many=True)
    raw_data_sources = RawDataSourceNestedPublicSerializer(many=True)
    information_requests = InformationRequestNestedPublicSerializer(many=True)

    class Meta:
        model = Dataset
        fields = [
            "id",
            "organization",
            "tables",
            "raw_data_sources",
            "information_requests",
            "slug",
            "name_en",
            "name_pt",
        ]


class DatasetSerializer(DatasetPublicSerializer):
    organization = serializers.HyperlinkedRelatedField(
        view_name="organization-private-detail", queryset=Organization.objects.all()
    )
    tables = TableNestedSerializer(many=True)
    raw_data_sources = RawDataSourceNestedSerializer(many=True)
    information_requests = InformationRequestNestedSerializer(many=True)


class DatasetNestedPublicSerializer(DatasetPublicSerializer):
    class Meta:
        model = Dataset
        fields = ["id", "slug", "name_en", "name_pt"]


class DatasetNestedSerializer(DatasetSerializer):
    class Meta:
        model = Dataset
        fields = ["id", "slug", "name_en", "name_pt"]


class OrganizationPublicSerializer(serializers.HyperlinkedModelSerializer):

    datasets = DatasetNestedPublicSerializer(many=True)

    class Meta:
        model = Organization
        fields = ["id", "datasets", "slug", "name_en", "name_pt", "website"]


class OrganizationSerializer(OrganizationPublicSerializer):
    datasets = DatasetNestedSerializer(many=True)
