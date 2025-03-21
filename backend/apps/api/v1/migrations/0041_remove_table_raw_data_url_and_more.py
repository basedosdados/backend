# Generated by Django 4.2.16 on 2024-11-05 23:04

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("v1", "0040_table_publishers_data_cleaners"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="table",
            name="raw_data_url",
        ),
        migrations.AlterField(
            model_name="analysis",
            name="analysis_type",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="analyses",
                to="v1.analysistype",
            ),
        ),
        migrations.AlterField(
            model_name="area",
            name="administrative_level",
            field=models.IntegerField(
                blank=True,
                choices=[(0, "0"), (1, "1"), (2, "2"), (3, "3"), (4, "4"), (5, "5")],
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="area",
            name="entity",
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={"category__slug": "spatial"},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="areas",
                to="v1.entity",
            ),
        ),
        migrations.AlterField(
            model_name="area",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="children",
                to="v1.area",
            ),
        ),
        migrations.AlterField(
            model_name="column",
            name="bigquery_type",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="columns",
                to="v1.bigquerytype",
            ),
        ),
        migrations.AlterField(
            model_name="column",
            name="directory_primary_key",
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={"is_primary_key": True, "table__is_directory": True},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="columns",
                to="v1.column",
            ),
        ),
        migrations.AlterField(
            model_name="column",
            name="observation_level",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="columns",
                to="v1.observationlevel",
            ),
        ),
        migrations.AlterField(
            model_name="column",
            name="status",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="columns",
                to="v1.status",
            ),
        ),
        migrations.AlterField(
            model_name="coverage",
            name="area",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="coverages",
                to="v1.area",
            ),
        ),
        migrations.AlterField(
            model_name="entity",
            name="category",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="entities",
                to="v1.entitycategory",
            ),
        ),
        migrations.AlterField(
            model_name="informationrequest",
            name="status",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="information_requests",
                to="v1.status",
            ),
        ),
        migrations.AlterField(
            model_name="observationlevel",
            name="entity",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="observation_levels",
                to="v1.entity",
            ),
        ),
        migrations.AlterField(
            model_name="organization",
            name="area",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="organizations",
                to="v1.area",
            ),
        ),
        migrations.AlterField(
            model_name="poll",
            name="entity",
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={"category__slug": "datetime"},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="polls",
                to="v1.entity",
            ),
        ),
        migrations.AlterField(
            model_name="qualitycheck",
            name="pipeline",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="quality_checks",
                to="v1.pipeline",
            ),
        ),
        migrations.AlterField(
            model_name="rawdatasource",
            name="availability",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="raw_data_sources",
                to="v1.availability",
            ),
        ),
        migrations.AlterField(
            model_name="rawdatasource",
            name="license",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="raw_data_sources",
                to="v1.license",
            ),
        ),
        migrations.AlterField(
            model_name="table",
            name="license",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="tables",
                to="v1.license",
            ),
        ),
        migrations.AlterField(
            model_name="table",
            name="partner_organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="partner_tables",
                to="v1.organization",
            ),
        ),
        migrations.AlterField(
            model_name="table",
            name="pipeline",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="tables",
                to="v1.pipeline",
            ),
        ),
        migrations.AlterField(
            model_name="update",
            name="entity",
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={"category__slug": "datetime"},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="updates",
                to="v1.entity",
            ),
        ),
    ]
