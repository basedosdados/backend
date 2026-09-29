# -*- coding: utf-8 -*-

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0029_remove_career_team_old_remove_career_role_old"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="account",
            name="username",
        ),
        migrations.AddField(
            model_name="account",
            name="phone",
            field=models.CharField(
                blank=True,
                help_text="Número em E.164, por exemplo +5511999999999",
                max_length=20,
                null=True,
                unique=True,
                validators=[
                    django.core.validators.RegexValidator(
                        message="Informe o celular em E.164, por exemplo +5511999999999.",
                        regex="^\\+[1-9]\\d{7,14}$",
                    )
                ],
                verbose_name="Celular",
            ),
        ),
    ]
