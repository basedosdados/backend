# -*- coding: utf-8 -*-
# Generated by Django 4.2.1 on 2023-05-17 23:12

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("v1", "0015_column_status_dataset_status_rawdatasource_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="column",
            name="is_primary_key",
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
        migrations.AddField(
            model_name="column",
            name="version",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="dataset",
            name="version",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="informationrequest",
            name="version",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="rawdatasource",
            name="version",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="table",
            name="version",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="column",
            name="status",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="columns",
                to="v1.status",
            ),
        ),
        migrations.AlterField(
            model_name="dataset",
            name="status",
            field=models.ForeignKey(
                blank=True,
                help_text="Status is used to indicate at what stage of development or publishing the dataset is.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="datasets",
                to="v1.status",
            ),
        ),
        migrations.AlterField(
            model_name="informationrequest",
            name="status",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="information_requests",
                to="v1.status",
            ),
        ),
        migrations.AlterField(
            model_name="rawdatasource",
            name="status",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="raw_data_sources",
                to="v1.status",
            ),
        ),
    ]
