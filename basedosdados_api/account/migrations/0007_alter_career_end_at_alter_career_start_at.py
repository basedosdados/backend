# -*- coding: utf-8 -*-
# Generated by Django 4.2.4 on 2023-08-21 19:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0006_add_internal_careers_model"),
    ]

    operations = [
        migrations.AlterField(
            model_name="career",
            name="end_at",
            field=models.DateField(blank=True, null=True, verbose_name="Data de Término"),
        ),
        migrations.AlterField(
            model_name="career",
            name="start_at",
            field=models.DateField(blank=True, null=True, verbose_name="Data de Início"),
        ),
    ]
