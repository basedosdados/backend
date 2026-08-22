# -*- coding: utf-8 -*-
from django.db import models
from django.utils import timezone


class DisabledFlowSchedule(models.Model):
    flow_name = models.CharField(max_length=255, unique=True)
    deployment_id = models.CharField(max_length=255)
    disabled_at = models.DateTimeField(default=timezone.now)
    is_schedule_active = models.BooleanField(default=False)
    reactivated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-disabled_at"]
        verbose_name = "Flow Schedule"
        verbose_name_plural = "Flow Schedules"

    def __str__(self):
        return self.flow_name
