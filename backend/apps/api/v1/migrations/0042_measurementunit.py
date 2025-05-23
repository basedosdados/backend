# Generated by Django 4.2.16 on 2024-11-05 23:20

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("v1", "0041_remove_table_raw_data_url_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="MeasurementUnit",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ("slug", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=255)),
            ],
            options={
                "verbose_name": "Measurement Unit",
                "verbose_name_plural": "Measurement Units",
                "db_table": "measurement_unit",
                "ordering": ["slug"],
            },
        ),
    ]
