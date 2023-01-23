# -*- coding: utf-8 -*-
from rest_framework import serializers

from basedosdados_api.api.v1.models import (
    Area,
    Coverage,
    License,
    Key,
    AnalysisType,
    Tag,
    Theme,
    Entity,
    TimeUnit,
    UpdateFrequency,
    # DirectoryPrimaryKey,
    # Dictionary,
    # Availability,
    # Language,
    # Status,
    # ObservationLevel,
    # EntityColumn,
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
    columns = ColumnNestedPublicSerializer(many=True, read_only=True)

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
    columns = ColumnNestedSerializer(many=True, read_only=True)


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
    columns = ColumnNestedPublicSerializer(many=True, read_only=True)

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
    columns = ColumnNestedSerializer(many=True, read_only=True)


class DatasetPublicSerializer(serializers.HyperlinkedModelSerializer):

    organization = serializers.HyperlinkedRelatedField(
        view_name="organization-public-detail", queryset=Organization.objects.all()
    )
    tables = TableNestedPublicSerializer(many=True, read_only=True)
    raw_data_sources = RawDataSourceNestedPublicSerializer(many=True, read_only=True)
    information_requests = InformationRequestNestedPublicSerializer(
        many=True, read_only=True
    )

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
    tables = TableNestedSerializer(many=True, read_only=True)
    raw_data_sources = RawDataSourceNestedSerializer(many=True, read_only=True)
    information_requests = InformationRequestNestedSerializer(many=True, read_only=True)


class DatasetNestedPublicSerializer(DatasetPublicSerializer):
    class Meta:
        model = Dataset
        fields = ["id", "slug", "name_en", "name_pt"]


class DatasetNestedSerializer(DatasetSerializer):
    class Meta:
        model = Dataset
        fields = ["id", "slug", "name_en", "name_pt"]


class OrganizationPublicSerializer(serializers.HyperlinkedModelSerializer):

    area = serializers.HyperlinkedRelatedField(
        view_name="area-public-detail", queryset=Area.objects.all()
    )
    datasets = DatasetNestedPublicSerializer(many=True, read_only=True)

    class Meta:
        model = Organization
        fields = ["id", "area", "datasets", "slug", "name_en", "name_pt", "website"]


class OrganizationSerializer(OrganizationPublicSerializer):
    area = serializers.HyperlinkedRelatedField(
        view_name="area-private-detail", queryset=Area.objects.all()
    )
    datasets = DatasetNestedSerializer(many=True, read_only=True)


class OrganizationNestedPublicSerializer(OrganizationPublicSerializer):
    class Meta:
        model = Organization
        fields = ["id", "slug", "name_en", "name_pt", "website"]


class OrganizationNestedSerializer(OrganizationSerializer):
    class Meta:
        model = Organization
        fields = ["id", "slug", "name_en", "name_pt", "website"]


class CoveragePublicSerializer(serializers.HyperlinkedModelSerializer):

    area = serializers.HyperlinkedRelatedField(
        view_name="area-public-detail", queryset=Area.objects.all()
    )
    keys = serializers.HyperlinkedRelatedField(
        view_name="key-public-detail", queryset=Key.objects.all(), many=True
    )

    class Meta:
        model = Coverage
        fields = ["id", "area", "temporal_coverage"]


class CoverageSerializer(CoveragePublicSerializer):
    area = serializers.HyperlinkedRelatedField(
        view_name="area-private-detail", queryset=Area.objects.all()
    )
    keys = serializers.HyperlinkedRelatedField(
        view_name="key-private-detail", queryset=Key.objects.all(), many=True
    )


class AnalysisTypePublicSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = AnalysisType
        fields = ["id", "name_en", "name_pt", "tag_en", "tag_pt"]


class AnalysisTypeSerializer(AnalysisTypePublicSerializer):
    pass


class TagPublicSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "slug", "name_en", "name_pt"]


class TagSerializer(TagPublicSerializer):
    pass


class KeyPublicSerializer(serializers.HyperlinkedModelSerializer):

    coverages = CoveragePublicSerializer(many=True, read_only=True)

    class Meta:
        model = Key
        fields = ["id", "coverages", "name", "value"]


class KeySerializer(KeyPublicSerializer):
    coverages = CoverageSerializer(many=True, read_only=True)


class LicensePublicSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = License
        fields = ["id", "slug", "name_en", "name_pt", "url"]


class LicenseSerializer(LicensePublicSerializer):
    pass


class AreaPublicSerializer(serializers.HyperlinkedModelSerializer):

    organizations = OrganizationNestedPublicSerializer(many=True, read_only=True)

    class Meta:
        model = Area
        fields = [
            "id",
            "organizations",
            "slug",
            "name_en",
            "name_pt",
            "area_ip_address_required",
        ]


class AreaSerializer(AreaPublicSerializer):
    organizations = OrganizationNestedSerializer(many=True, read_only=True)


class ThemePublicSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Theme
        fields = ["id", "slug", "name_en", "name_pt" "logo_url"]


class ThemeSerializer(ThemePublicSerializer):
    pass


class EntityPublicSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Entity
        fields = ["id", "slug", "name_en", "name_pt"]


class EntitySerializer(EntityPublicSerializer):
    pass


class TimeUnitPublicSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = TimeUnit
        fields = ["id", "slug", "name_en", "name_pt"]


class TimeUnitSerializer(TimeUnitPublicSerializer):
    pass


class UpdateFrequencyPublicSerializer(serializers.HyperlinkedModelSerializer):
    time_unit = serializers.HyperlinkedRelatedField(
        view_name="timeunit-public-detail", queryset=TimeUnit.objects.all()
    )

    class Meta:
        model = UpdateFrequency
        fields = ["id", "time_unit", "number"]


class UpdateFrequencySerializer(UpdateFrequencyPublicSerializer):
    time_unit = serializers.HyperlinkedRelatedField(
        view_name="timeunit-private-detail", queryset=TimeUnit.objects.all()
    )
