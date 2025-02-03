# Generated by Django 4.2.16 on 2024-11-04 03:54

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("v1", "0047_initialize_observation_level_order"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="observationlevel",
            options={
                "ordering": ["order"],
                "verbose_name": "Observation Level",
                "verbose_name_plural": "Observation Levels",
            },
        ),
    ]
