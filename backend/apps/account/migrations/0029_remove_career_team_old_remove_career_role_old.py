# -*- coding: utf-8 -*-

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0028_alter_account_uuid"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="career",
            name="team_old",
        ),
        migrations.RemoveField(
            model_name="career",
            name="role_old",
        ),
    ]
