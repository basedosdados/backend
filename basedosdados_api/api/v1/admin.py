# -*- coding: utf-8 -*-
from django.contrib import admin

from basedosdados_api.api.v1.models import (
    Organization,
    Dataset,
    Table,
    BigQueryTypes,
    Column,
    CloudTable,
)

admin.site.register(Organization)
admin.site.register(Dataset)
admin.site.register(Table)
admin.site.register(BigQueryTypes)
admin.site.register(Column)
admin.site.register(CloudTable)
