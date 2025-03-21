# Generated by Django 4.2.16 on 2024-11-06 04:30

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("v1", "0049_poll_pipeline"),
    ]

    operations = [
        migrations.AddField(
            model_name="table",
            name="is_deprecated",
            field=models.BooleanField(
                default=False,
                help_text="We stopped maintaining this table for some reason. Examples: raw data deprecated, new version elsewhere, etc.",
            ),
        ),
    ]
