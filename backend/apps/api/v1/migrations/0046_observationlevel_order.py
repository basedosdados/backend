# -*- coding: utf-8 -*-
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("v1", "0045_add_measurement_categories_and_units"),
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
