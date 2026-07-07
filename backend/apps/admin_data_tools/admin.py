# -*- coding: utf-8 -*-
from django.contrib import admin
from django.utils import timezone

from ._prefect3_client import Prefect3Client
from .models import DisabledFlowSchedule


@admin.register(DisabledFlowSchedule)
class DisabledFlowScheduleAdmin(admin.ModelAdmin):
    list_display = [
        "flow_name",
        "deployment_id",
        "disabled_at",
        "is_schedule_active",
        "reactivated_at",
    ]
    list_filter = ["is_schedule_active"]
    readonly_fields = ["flow_name", "deployment_id", "disabled_at", "reactivated_at"]
    fields = ["flow_name", "deployment_id", "disabled_at", "is_schedule_active", "reactivated_at"]

    def save_model(self, request, obj, form, change):
        if change and "is_schedule_active" in form.changed_data:
            client = Prefect3Client()
            if obj.is_schedule_active:
                obj.reactivated_at = timezone.now()
                client.set_paused(obj.deployment_id, paused=False)
            else:
                obj.reactivated_at = None
                client.set_paused(obj.deployment_id, paused=True)

        super().save_model(request, obj, form, change)
