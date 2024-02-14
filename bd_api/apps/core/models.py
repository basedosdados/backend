# -*- coding: utf-8 -*-
from uuid import uuid4

from django.db import models

from bd_api.custom.model import BaseModel


class Metadata(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid4)
    key = models.JSONField(default=dict, blank=False, null=False)
    value = models.JSONField(default=dict, blank=False, null=False)
