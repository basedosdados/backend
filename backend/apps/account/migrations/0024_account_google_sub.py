# -*- coding: utf-8 -*-
# Generated manually for google_sub field

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0023_alter_career_role_old_alter_career_team_old"),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE account ADD COLUMN IF NOT EXISTS google_sub VARCHAR(255) NULL;",
            reverse_sql="ALTER TABLE account DROP COLUMN google_sub;",
            state_operations=[
                migrations.AddField(
                    model_name="account",
                    name="google_sub",
                    field=models.CharField(
                        blank=True, max_length=255, null=True, unique=True, verbose_name="Google Sub"
                    ),
                ),
            ],
        ),
    ]
