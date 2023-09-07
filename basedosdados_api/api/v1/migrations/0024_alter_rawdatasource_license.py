# -*- coding: utf-8 -*-
# Generated by Django 4.2.4 on 2023-08-29 23:00

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("v1", "0023_datetimerange_is_closed"),
    ]

    operations = [
        migrations.AlterField(
            model_name="rawdatasource",
            name="license",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="raw_data_sources",
                to="v1.license",
            ),
        ),
    ]
