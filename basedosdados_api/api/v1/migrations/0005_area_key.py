# Generated by Django 4.1.3 on 2023-02-23 21:55

import basedosdados_api.api.v1.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("v1", "0004_remove_informationrequest_observation_level_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="area",
            name="key",
            field=models.CharField(
                max_length=255,
                null=True,
                validators=[
                    basedosdados_api.api.v1.validators.validate_area_key,
                    basedosdados_api.api.v1.validators.validate_is_valid_area_key,
                ],
            ),
        ),
    ]
