# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib import admin
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from ._prefect3_client import Prefect3Client
from .models import DisabledFlowSchedule


@admin.register(DisabledFlowSchedule)
class DisabledFlowScheduleAdmin(admin.ModelAdmin):
    list_display = [
        "flow_name_display",
        "deployment_id",
        "disabled_at",
        "is_schedule_active",
        "reactivated_at",
    ]
    # flow_name_display already renders its own <a> to the change page. Must be
    # None, not [] — Django treats [] as "unset" and falls back to
    # auto-linking the first column, nesting an <a> around it either way.
    list_display_links = None
    list_filter = ["is_schedule_active"]
    search_fields = ["flow_name"]
    readonly_fields = ["flow_name_display", "deployment_id", "disabled_at", "reactivated_at"]
    fields = [
        "flow_name_display",
        "deployment_id",
        "disabled_at",
        "is_schedule_active",
        "reactivated_at",
    ]

    def flow_name_display(self, obj):
        """Flow name linking to the Django change page, plus a button that opens
        the deployment directly in Prefect 3 — built by hand (not via
        list_display_links) so the Prefect link isn't nested inside another
        <a>, which Django's automatic column-link wrapping would do."""
        change_url = reverse(
            f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change", args=[obj.pk]
        )
        prefect_ui_url = settings.PREFECT3_API_URL.removesuffix("/api")
        deployment_url = f"{prefect_ui_url}/v2/deployments/deployment/{obj.deployment_id}?tab=Runs"
        return format_html(
            '<a href="{}">{}</a> <a href="{}" target="_blank" rel="noopener" '
            'class="btn btn-secondary btn-sm" style="padding: 1px 6px;">Prefect ↗</a>',
            change_url,
            obj.flow_name,
            deployment_url,
        )

    flow_name_display.short_description = "Flow Name"
    flow_name_display.admin_order_field = "flow_name"

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
