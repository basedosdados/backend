# -*- coding: utf-8 -*-
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("v1", "0042_measurementunit"),
    ]

    operations = [
        migrations.AddField(
            model_name="measurementunit",
            name="name_pt",
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="measurementunit",
            name="name_en",
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="measurementunit",
            name="name_es",
            field=models.CharField(max_length=255, null=True),
        ),
    ]
