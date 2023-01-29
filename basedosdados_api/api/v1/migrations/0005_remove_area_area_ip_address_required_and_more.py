# -*- coding: utf-8 -*-
# Generated by Django 4.1.3 on 2023-01-29 22:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("v1", "0004_analysistype_availability_coverage_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="area",
            name="area_ip_address_required",
        ),
        migrations.RemoveField(
            model_name="area",
            name="name_en",
        ),
        migrations.RemoveField(
            model_name="area",
            name="name_pt",
        ),
        migrations.RemoveField(
            model_name="column",
            name="coverage_by_dictionary",
        ),
        migrations.RemoveField(
            model_name="column",
            name="has_sensitive_data",
        ),
        migrations.RemoveField(
            model_name="table",
            name="data_cleaned_code_url",
        ),
        migrations.RemoveField(
            model_name="table",
            name="data_cleaned_description",
        ),
        migrations.RemoveField(
            model_name="table",
            name="number_of_rows",
        ),
        migrations.AddField(
            model_name="column",
            name="contains_sensitive_data",
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
        migrations.AddField(
            model_name="column",
            name="coverages",
            field=models.ManyToManyField(related_name="columns", to="v1.coverage"),
        ),
        migrations.AddField(
            model_name="column",
            name="covered_by_dictionary",
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
        migrations.AddField(
            model_name="dataset",
            name="description",
            field=models.TextField(blank=True, null=True),
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
            model_name="informationrequest",
            name="coverages",
            field=models.ManyToManyField(
                related_name="information_requests", to="v1.coverage"
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="description",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="organization",
            name="facebook",
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="organization",
            name="instagram",
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="organization",
            name="linkedin",
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="organization",
            name="twitter",
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="rawdatasource",
            name="area_ip_address_required",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="rawdatasource",
            name="coverages",
            field=models.ManyToManyField(
                related_name="raw_data_sources", to="v1.coverage"
            ),
        ),
        migrations.AddField(
            model_name="table",
            name="coverages",
            field=models.ManyToManyField(related_name="tables", to="v1.coverage"),
        ),
        migrations.AddField(
            model_name="table",
            name="data_cleaning_code_url",
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="table",
            name="data_cleaning_description",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="table",
            name="number_columns",
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="table",
            name="number_rows",
            field=models.BigIntegerField(blank=True, null=True),
        ),
    ]
