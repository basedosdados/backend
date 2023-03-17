# Generated by Django 4.1.7 on 2023-03-17 01:15

import basedosdados_api.account.models
import basedosdados_api.account.storage
import basedosdados_api.api.v1.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0003_alter_account_picture"),
    ]

    operations = [
        migrations.AlterField(
            model_name="account",
            name="picture",
            field=models.ImageField(
                blank=True,
                null=True,
                storage=basedosdados_api.account.storage.OverwriteStorage(),
                upload_to=basedosdados_api.account.models.image_path_and_rename,
                validators=[
                    basedosdados_api.api.v1.validators.validate_is_valid_image_format
                ],
                verbose_name="Imagem",
            ),
        ),
    ]
