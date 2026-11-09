# -*- coding: utf-8 -*-
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("v1", "0058_column_coverage_entity"),
    ]

    operations = [
        migrations.AddField(
            model_name="researcher",
            name="status",
            field=models.ForeignKey(
                blank=True,
                help_text="Use under_review or excluded to hide the researcher from the website",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="researchers",
                to="v1.status",
            ),
        ),
    ]
