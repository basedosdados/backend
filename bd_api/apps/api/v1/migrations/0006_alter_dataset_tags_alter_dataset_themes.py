# -*- coding: utf-8 -*-
# Generated by Django 4.1.7 on 2023-04-30 15:26

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("v1", "0005_alter_table_license_alter_table_partner_organization_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dataset",
            name="tags",
            field=models.ManyToManyField(
                blank=True,
                help_text="Tags are used to group datasets by topic",
                related_name="datasets",
                to="v1.tag",
            ),
        ),
        migrations.AlterField(
            model_name="dataset",
            name="themes",
            field=models.ManyToManyField(
                help_text="Themes are used to group datasets by topic",
                related_name="datasets",
                to="v1.theme",
            ),
        ),
    ]
