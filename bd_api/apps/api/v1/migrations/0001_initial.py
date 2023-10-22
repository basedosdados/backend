# -*- coding: utf-8 -*-
# Generated by Django 4.1.7 on 2023-03-28 16:51

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import bd_api.apps.account.storage
import bd_api.apps.api.v1.models
import bd_api.apps.api.v1.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AnalysisType",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
                ),
                ("slug", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=255)),
                ("name_pt", models.CharField(max_length=255, null=True)),
                ("name_en", models.CharField(max_length=255, null=True)),
                ("name_es", models.CharField(max_length=255, null=True)),
                ("tag", models.CharField(max_length=255)),
                ("tag_pt", models.CharField(max_length=255, null=True)),
                ("tag_en", models.CharField(max_length=255, null=True)),
                ("tag_es", models.CharField(max_length=255, null=True)),
            ],
            options={
                "verbose_name": "Analysis Type",
                "verbose_name_plural": "Analysis Types",
                "db_table": "analysis_type",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Area",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
                ),
                ("slug", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=255)),
                ("name_pt", models.CharField(max_length=255, null=True)),
                ("name_en", models.CharField(max_length=255, null=True)),
                ("name_es", models.CharField(max_length=255, null=True)),
            ],
            options={
                "verbose_name": "Area",
                "verbose_name_plural": "Areas",
                "db_table": "area",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Availability",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
                ),
                ("slug", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=255)),
                ("name_pt", models.CharField(max_length=255, null=True)),
                ("name_en", models.CharField(max_length=255, null=True)),
                ("name_es", models.CharField(max_length=255, null=True)),
            ],
            options={
                "verbose_name": "Availability",
                "verbose_name_plural": "Availabilities",
                "db_table": "availability",
                "ordering": ["slug"],
            },
        ),
        migrations.CreateModel(
            name="BigQueryType",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
                ),
                ("name", models.CharField(max_length=255)),
            ],
            options={
                "verbose_name": "BigQuery Type",
                "verbose_name_plural": "BigQuery Types",
                "db_table": "bigquery_type",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Column",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
                ),
                ("name", models.CharField(max_length=255)),
                ("name_pt", models.CharField(max_length=255, null=True)),
                ("name_en", models.CharField(max_length=255, null=True)),
                ("name_es", models.CharField(max_length=255, null=True)),
                ("description", models.TextField(blank=True, null=True)),
                ("description_pt", models.TextField(blank=True, null=True)),
                ("description_en", models.TextField(blank=True, null=True)),
                ("description_es", models.TextField(blank=True, null=True)),
                (
                    "covered_by_dictionary",
                    models.BooleanField(blank=True, default=False, null=True),
                ),
                (
                    "measurement_unit",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "contains_sensitive_data",
                    models.BooleanField(blank=True, default=False, null=True),
                ),
                ("observations", models.TextField(blank=True, null=True)),
                ("observations_pt", models.TextField(blank=True, null=True)),
                ("observations_en", models.TextField(blank=True, null=True)),
                ("observations_es", models.TextField(blank=True, null=True)),
                ("is_in_staging", models.BooleanField(default=True)),
                ("is_partition", models.BooleanField(default=False)),
                (
                    "bigquery_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="columns",
                        to="v1.bigquerytype",
                    ),
                ),
                (
                    "directory_primary_key",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="columns",
                        to="v1.column",
                    ),
                ),
            ],
            options={
                "verbose_name": "Column",
                "verbose_name_plural": "Columns",
                "db_table": "column",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Coverage",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
                ),
                (
                    "area",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="coverages",
                        to="v1.area",
                    ),
                ),
                (
                    "column",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="coverages",
                        to="v1.column",
                    ),
                ),
            ],
            options={
                "verbose_name": "Coverage",
                "verbose_name_plural": "Coverages",
                "db_table": "coverage",
                "ordering": ["id"],
            },
        ),
        migrations.CreateModel(
            name="Dataset",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
                ),
                ("slug", models.SlugField(max_length=255)),
                ("name", models.CharField(max_length=255)),
                ("name_pt", models.CharField(max_length=255, null=True)),
                ("name_en", models.CharField(max_length=255, null=True)),
                ("name_es", models.CharField(max_length=255, null=True)),
                ("description", models.TextField(blank=True, null=True)),
                ("description_pt", models.TextField(blank=True, null=True)),
                ("description_en", models.TextField(blank=True, null=True)),
                ("description_es", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Dataset",
                "verbose_name_plural": "Datasets",
                "db_table": "dataset",
                "ordering": ["slug"],
            },
        ),
        migrations.CreateModel(
            name="Dictionary",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
                ),
                (
                    "column",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dictionaries",
                        to="v1.column",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Entity",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
                ),
                ("slug", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=255)),
                ("name_pt", models.CharField(max_length=255, null=True)),
                ("name_en", models.CharField(max_length=255, null=True)),
                ("name_es", models.CharField(max_length=255, null=True)),
            ],
            options={
                "verbose_name": "Entity",
                "verbose_name_plural": "Entities",
                "db_table": "entity",
                "ordering": ["slug"],
            },
        ),
        migrations.CreateModel(
            name="EntityCategory",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
                ),
                ("slug", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=255)),
                ("name_pt", models.CharField(max_length=255, null=True)),
                ("name_en", models.CharField(max_length=255, null=True)),
                ("name_es", models.CharField(max_length=255, null=True)),
            ],
            options={
                "verbose_name": "EntityCategory",
                "verbose_name_plural": "EntityCategories",
                "db_table": "entity_category",
                "ordering": ["slug"],
            },
        ),
        migrations.CreateModel(
            name="InformationRequest",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("origin", models.TextField(blank=True, max_length=500, null=True)),
                ("number", models.CharField(max_length=255)),
                ("url", models.URLField(blank=True, max_length=500, null=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("data_url", models.URLField(blank=True, max_length=500, null=True)),
                ("observations", models.TextField(blank=True, null=True)),
                ("observations_pt", models.TextField(blank=True, null=True)),
                ("observations_en", models.TextField(blank=True, null=True)),
                ("observations_es", models.TextField(blank=True, null=True)),
                (
                    "dataset",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="information_requests",
                        to="v1.dataset",
                    ),
                ),
                (
                    "started_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="information_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Information Request",
                "verbose_name_plural": "Information Requests",
                "db_table": "information_request",
                "ordering": ["number"],
            },
        ),
        migrations.CreateModel(
            name="Language",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
                ),
                ("slug", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=255)),
                ("name_pt", models.CharField(max_length=255, null=True)),
                ("name_en", models.CharField(max_length=255, null=True)),
                ("name_es", models.CharField(max_length=255, null=True)),
            ],
            options={
                "verbose_name": "Language",
                "verbose_name_plural": "Languages",
                "db_table": "language",
                "ordering": ["slug"],
            },
        ),
        migrations.CreateModel(
            name="License",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
                ),
                ("slug", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=255)),
                ("name_pt", models.CharField(max_length=255, null=True)),
                ("name_en", models.CharField(max_length=255, null=True)),
                ("name_es", models.CharField(max_length=255, null=True)),
                ("url", models.URLField()),
            ],
            options={
                "verbose_name": "License",
                "verbose_name_plural": "Licenses",
                "db_table": "license",
                "ordering": ["slug"],
            },
        ),
        migrations.CreateModel(
            name="Organization",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
                ),
                ("slug", models.SlugField(max_length=255)),
                ("name", models.CharField(max_length=255)),
                ("name_pt", models.CharField(max_length=255, null=True)),
                ("name_en", models.CharField(max_length=255, null=True)),
                ("name_es", models.CharField(max_length=255, null=True)),
                ("description", models.TextField(blank=True, null=True)),
                ("description_pt", models.TextField(blank=True, null=True)),
                ("description_en", models.TextField(blank=True, null=True)),
                ("description_es", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("website", models.URLField(blank=True, max_length=255, null=True)),
                ("twitter", models.URLField(blank=True, null=True)),
                ("facebook", models.URLField(blank=True, null=True)),
                ("linkedin", models.URLField(blank=True, null=True)),
                ("instagram", models.URLField(blank=True, null=True)),
                (
                    "picture",
                    models.ImageField(
                        blank=True,
                        null=True,
                        storage=bd_api.apps.account.storage.OverwriteStorage(),
                        upload_to=bd_api.apps.api.v1.models.image_path_and_rename,
                        validators=[bd_api.apps.api.v1.validators.validate_is_valid_image_format],
                        verbose_name="Imagem",
                    ),
                ),
                (
                    "area",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="organizations",
                        to="v1.area",
                    ),
                ),
            ],
            options={
                "verbose_name": "Organization",
                "verbose_name_plural": "Organizations",
                "db_table": "organization",
                "ordering": ["slug"],
            },
        ),
        migrations.CreateModel(
            name="Pipeline",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
                ),
                ("github_url", models.URLField()),
            ],
            options={
                "verbose_name": "Pipeline",
                "verbose_name_plural": "Pipelines",
                "db_table": "pipeline",
                "ordering": ["github_url"],
            },
        ),
        migrations.CreateModel(
            name="RawDataSource",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
                ),
                ("name", models.CharField(max_length=255)),
                ("name_pt", models.CharField(max_length=255, null=True)),
                ("name_en", models.CharField(max_length=255, null=True)),
                ("name_es", models.CharField(max_length=255, null=True)),
                ("description", models.TextField(blank=True, null=True)),
                ("description_pt", models.TextField(blank=True, null=True)),
                ("description_en", models.TextField(blank=True, null=True)),
                ("description_es", models.TextField(blank=True, null=True)),
                ("url", models.URLField(blank=True, max_length=500, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("contains_structure_data", models.BooleanField(default=False)),
                ("contains_api", models.BooleanField(default=False)),
                ("is_free", models.BooleanField(default=False)),
                ("required_registration", models.BooleanField(default=False)),
                (
                    "area_ip_address_required",
                    models.ManyToManyField(
                        blank=True, related_name="raw_data_sources", to="v1.area"
                    ),
                ),
                (
                    "availability",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="raw_data_sources",
                        to="v1.availability",
                    ),
                ),
                (
                    "dataset",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="raw_data_sources",
                        to="v1.dataset",
                    ),
                ),
                (
                    "languages",
                    models.ManyToManyField(
                        blank=True, related_name="raw_data_sources", to="v1.language"
                    ),
                ),
                (
                    "license",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="raw_data_sources",
                        to="v1.license",
                    ),
                ),
            ],
            options={
                "verbose_name": "Raw Data Source",
                "verbose_name_plural": "Raw Data Sources",
                "db_table": "raw_data_source",
                "ordering": ["url"],
            },
        ),
        migrations.CreateModel(
            name="Status",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
                ),
                ("slug", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=255)),
                ("name_pt", models.CharField(max_length=255, null=True)),
                ("name_en", models.CharField(max_length=255, null=True)),
                ("name_es", models.CharField(max_length=255, null=True)),
            ],
            options={
                "verbose_name": "Status",
                "verbose_name_plural": "Statuses",
                "db_table": "status",
                "ordering": ["slug"],
            },
        ),
        migrations.CreateModel(
            name="Table",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
                ),
                ("slug", models.SlugField(max_length=255)),
                ("name", models.CharField(max_length=255)),
                ("name_pt", models.CharField(max_length=255, null=True)),
                ("name_en", models.CharField(max_length=255, null=True)),
                ("name_es", models.CharField(max_length=255, null=True)),
                ("description", models.TextField(blank=True, null=True)),
                ("description_pt", models.TextField(blank=True, null=True)),
                ("description_en", models.TextField(blank=True, null=True)),
                ("description_es", models.TextField(blank=True, null=True)),
                (
                    "is_directory",
                    models.BooleanField(blank=True, default=False, null=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("data_cleaning_description", models.TextField(blank=True, null=True)),
                ("data_cleaning_code_url", models.URLField(blank=True, null=True)),
                (
                    "raw_data_url",
                    models.URLField(blank=True, max_length=500, null=True),
                ),
                ("auxiliary_files_url", models.URLField(blank=True, null=True)),
                ("architecture_url", models.URLField(blank=True, null=True)),
                (
                    "source_bucket_name",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "uncompressed_file_size",
                    models.BigIntegerField(blank=True, null=True),
                ),
                ("compressed_file_size", models.BigIntegerField(blank=True, null=True)),
                ("number_rows", models.BigIntegerField(blank=True, null=True)),
                ("number_columns", models.BigIntegerField(blank=True, null=True)),
                (
                    "data_cleaned_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tables_cleaned",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "dataset",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tables",
                        to="v1.dataset",
                    ),
                ),
                (
                    "license",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tables",
                        to="v1.license",
                    ),
                ),
                (
                    "partner_organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="partner_tables",
                        to="v1.organization",
                    ),
                ),
                (
                    "pipeline",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tables",
                        to="v1.pipeline",
                    ),
                ),
                (
                    "published_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tables_published",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "status",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="tables",
                        to="v1.status",
                    ),
                ),
            ],
            options={
                "verbose_name": "Table",
                "verbose_name_plural": "Tables",
                "db_table": "table",
                "ordering": ["slug"],
            },
        ),
        migrations.CreateModel(
            name="Tag",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
                ),
                ("slug", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=255)),
                ("name_pt", models.CharField(max_length=255, null=True)),
                ("name_en", models.CharField(max_length=255, null=True)),
                ("name_es", models.CharField(max_length=255, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Tag",
                "verbose_name_plural": "Tags",
                "db_table": "tag",
                "ordering": ["slug"],
            },
        ),
        migrations.CreateModel(
            name="Theme",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
                ),
                ("slug", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=255)),
                ("name_pt", models.CharField(max_length=255, null=True)),
                ("name_en", models.CharField(max_length=255, null=True)),
                ("name_es", models.CharField(max_length=255, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Theme",
                "verbose_name_plural": "Themes",
                "db_table": "theme",
                "ordering": ["slug"],
            },
        ),
        migrations.CreateModel(
            name="Update",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
                ),
                ("frequency", models.IntegerField()),
                ("lag", models.IntegerField(blank=True, null=True)),
                ("latest", models.DateTimeField(blank=True, null=True)),
                (
                    "entity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="updates",
                        to="v1.entity",
                    ),
                ),
                (
                    "information_request",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="updates",
                        to="v1.informationrequest",
                    ),
                ),
                (
                    "raw_data_source",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="updates",
                        to="v1.rawdatasource",
                    ),
                ),
                (
                    "table",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="updates",
                        to="v1.table",
                    ),
                ),
            ],
            options={
                "verbose_name": "Update",
                "verbose_name_plural": "Updates",
                "db_table": "update",
                "ordering": ["frequency"],
            },
        ),
        migrations.CreateModel(
            name="ObservationLevel",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
                ),
                (
                    "entity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="observation_levels",
                        to="v1.entity",
                    ),
                ),
                (
                    "information_request",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="observation_levels",
                        to="v1.informationrequest",
                    ),
                ),
                (
                    "raw_data_source",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="observation_levels",
                        to="v1.rawdatasource",
                    ),
                ),
                (
                    "table",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="observation_levels",
                        to="v1.table",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Key",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
                ),
                ("name", models.CharField(max_length=255)),
                ("value", models.CharField(max_length=255)),
                (
                    "dictionary",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="keys",
                        to="v1.dictionary",
                    ),
                ),
            ],
            options={
                "verbose_name": "Key",
                "verbose_name_plural": "Keys",
                "db_table": "keys",
                "ordering": ["name"],
            },
        ),
        migrations.AddField(
            model_name="informationrequest",
            name="status",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="information_requests",
                to="v1.status",
            ),
        ),
        migrations.AddField(
            model_name="entity",
            name="category",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="entities",
                to="v1.entitycategory",
            ),
        ),
        migrations.CreateModel(
            name="DateTimeRange",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
                ),
                ("start_year", models.IntegerField(blank=True, null=True)),
                ("start_semester", models.IntegerField(blank=True, null=True)),
                ("start_quarter", models.IntegerField(blank=True, null=True)),
                ("start_month", models.IntegerField(blank=True, null=True)),
                ("start_day", models.IntegerField(blank=True, null=True)),
                ("start_hour", models.IntegerField(blank=True, null=True)),
                ("start_minute", models.IntegerField(blank=True, null=True)),
                ("start_second", models.IntegerField(blank=True, null=True)),
                ("end_year", models.IntegerField(blank=True, null=True)),
                ("end_semester", models.IntegerField(blank=True, null=True)),
                ("end_quarter", models.IntegerField(blank=True, null=True)),
                ("end_month", models.IntegerField(blank=True, null=True)),
                ("end_day", models.IntegerField(blank=True, null=True)),
                ("end_hour", models.IntegerField(blank=True, null=True)),
                ("end_minute", models.IntegerField(blank=True, null=True)),
                ("end_second", models.IntegerField(blank=True, null=True)),
                ("interval", models.IntegerField(blank=True, null=True)),
                (
                    "coverage",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="datetime_ranges",
                        to="v1.coverage",
                    ),
                ),
            ],
            options={
                "verbose_name": "DateTime Range",
                "verbose_name_plural": "DateTime Ranges",
                "db_table": "datetime_range",
                "ordering": ["id"],
            },
        ),
        migrations.AddField(
            model_name="dataset",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="datasets",
                to="v1.organization",
            ),
        ),
        migrations.AddField(
            model_name="dataset",
            name="tags",
            field=models.ManyToManyField(related_name="datasets", to="v1.tag"),
        ),
        migrations.AddField(
            model_name="dataset",
            name="themes",
            field=models.ManyToManyField(related_name="datasets", to="v1.theme"),
        ),
        migrations.AddField(
            model_name="coverage",
            name="information_request",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="coverages",
                to="v1.informationrequest",
            ),
        ),
        migrations.AddField(
            model_name="coverage",
            name="key",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="coverages",
                to="v1.key",
            ),
        ),
        migrations.AddField(
            model_name="coverage",
            name="raw_data_source",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="coverages",
                to="v1.rawdatasource",
            ),
        ),
        migrations.AddField(
            model_name="coverage",
            name="table",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="coverages",
                to="v1.table",
            ),
        ),
        migrations.AddField(
            model_name="column",
            name="observation_level",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="columns",
                to="v1.observationlevel",
            ),
        ),
        migrations.AddField(
            model_name="column",
            name="table",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="columns",
                to="v1.table",
            ),
        ),
        migrations.CreateModel(
            name="CloudTable",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
                ),
                ("gcp_project_id", models.CharField(max_length=255)),
                ("gcp_dataset_id", models.CharField(max_length=255)),
                ("gcp_table_id", models.CharField(max_length=255)),
                (
                    "columns",
                    models.ManyToManyField(related_name="cloud_tables", to="v1.column"),
                ),
                (
                    "table",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cloud_tables",
                        to="v1.table",
                    ),
                ),
            ],
            options={
                "verbose_name": "Cloud Table",
                "verbose_name_plural": "Cloud Tables",
                "db_table": "cloud_table",
                "ordering": ["id"],
            },
        ),
        migrations.AddConstraint(
            model_name="table",
            constraint=models.UniqueConstraint(
                fields=("dataset", "slug"), name="constraint_dataset_table_slug"
            ),
        ),
    ]