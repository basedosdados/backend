# -*- coding: utf-8 -*-
from django.contrib import admin
from django.utils import timezone

from backend.apps.admin_data_tools.management.commands._disable_unhealthy_flow_schedules.service import (  # noqa: E501
    FlowService,
)

from .models import DisabledFlowSchedule


@admin.register(DisabledFlowSchedule)
class DisabledFlowScheduleAdmin(admin.ModelAdmin):
    list_display = ["flow_name", "flow_id", "disabled_at", "is_schedule_active", "reactivated_at"]
    list_filter = ["is_schedule_active"]
    readonly_fields = ["flow_name", "flow_id", "disabled_at", "reactivated_at"]
    fields = ["flow_name", "flow_id", "disabled_at", "is_schedule_active", "reactivated_at"]

    def save_model(self, request, obj, form, change):
        if change and "is_schedule_active" in form.changed_data:
            service = FlowService()
            if obj.is_schedule_active:
                obj.reactivated_at = timezone.now()
                service.set_flow_schedule(flow_id=obj.flow_id, active=True)
            else:
                obj.reactivated_at = None
                service.disable_flow_schedule(flow_id=obj.flow_id)

        super().save_model(request, obj, form, change)
