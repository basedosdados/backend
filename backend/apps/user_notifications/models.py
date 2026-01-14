# -*- coding: utf-8 -*-
# Create your models here.
# -*- coding: utf-8 -*-
import logging
from uuid import uuid4

from django.db import models

from backend.apps.account.models import Account
from backend.apps.api.v1.models import Table
from backend.custom.model import BaseModel

logger = logging.getLogger("django.request")


class TableUpdateSubscription(BaseModel):
    """ "Table Update Subscription"""

    id = models.UUIDField(primary_key=True, default=uuid4)
    table = models.ForeignKey(Table, on_delete=models.CASCADE)
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    deactivate_at = models.DateTimeField(null=True, blank=True)
    last_notification = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return f"Subscription {self.id} - Table: {self.table.name}, User: {self.user.username}"

    class Meta:
        verbose_name = "Table Update Subscription"
        verbose_name_plural = "Table Update Subscriptions"
