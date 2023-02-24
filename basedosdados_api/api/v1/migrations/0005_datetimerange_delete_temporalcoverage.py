# -*- coding: utf-8 -*-
# Generated by Django 4.1.3 on 2023-02-23 23:31

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("v1", "0004_remove_informationrequest_observation_level_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="DateTimeRange",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, primary_key=True, serialize=False
                    ),
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
        migrations.DeleteModel(
            name="TemporalCoverage",
        ),
    ]
