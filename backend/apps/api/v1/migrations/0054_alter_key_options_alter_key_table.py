# -*- coding: utf-8 -*-
# Generated by Django 4.2.18 on 2025-02-20 11:14

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("v1", "0053_remove_rawdatasource_required_registration_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="key",
            options={
                "ordering": ["name"],
                "verbose_name": "Dictionary Key",
                "verbose_name_plural": "Dictionary Keys",
            },
        ),
        migrations.AlterModelTable(
            name="key",
            table="dictionary_key",
        ),
    ]
