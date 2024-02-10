# -*- coding: utf-8 -*-
# Generated by Django 4.1.7 on 2023-03-30 20:40

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="account",
            name="full_name",
            field=models.CharField(
                blank=True, max_length=100, null=True, verbose_name="Nome Completo"
            ),
        ),
    ]
