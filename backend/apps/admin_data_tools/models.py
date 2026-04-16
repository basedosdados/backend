# -*- coding: utf-8 -*-
from django.db import models


class DisabledFlowSchedule(models.Model):
    flow_name = models.CharField(max_length=255, unique=True)
    flow_id = models.CharField(max_length=255)
    disabled_at = models.DateTimeField(auto_now_add=True)
    is_schedule_active = models.BooleanField(default=False)
    reactivated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-disabled_at"]
        verbose_name = "Disabled Flow Schedule"
        verbose_name_plural = "Disabled Flow Schedules"

    def __str__(self):
        return self.flow_name
