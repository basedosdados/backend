# -*- coding: utf-8 -*-
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("v1", "0038_rename_level_area_administrative_level"),
    ]

    operations = [
        migrations.AddField(
            model_name="observationlevel",
            name="order",
            field=models.PositiveIntegerField(
                db_index=True, default=0, editable=False, verbose_name="order"
            ),
            preserve_default=False,
        ),
    ] 