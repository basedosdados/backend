# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html, format_html_join

from .models import DisabledFlowSchedule
from .schedule_actions import apply_schedule_state


@admin.action(description="Ativar agendamento selecionado(s)")
def activate_selected(modeladmin, request, queryset):
    _bulk_apply_schedule_state(request, queryset, active=True)


@admin.action(description="Desativar agendamento selecionado(s)")
def deactivate_selected(modeladmin, request, queryset):
    _bulk_apply_schedule_state(request, queryset, active=False)


def _bulk_apply_schedule_state(request, queryset, active: bool) -> None:
    """Apply `apply_schedule_state` to every selected row that isn't already
    in the desired state, and report a summary via the admin's message
    framework. One failure (e.g. Prefect unreachable) doesn't abort the rest
    of the batch — it's reported alongside whatever did succeed."""
    targets = list(queryset.exclude(is_schedule_active=active).order_by("pk"))
    skipped = queryset.count() - len(targets)

    changed = 0
    errors = []
    for record in targets:
        try:
            apply_schedule_state(record, active)
            changed += 1
        except Exception as exc:
            errors.append(f"{record.flow_name}: {exc}")

    verb = "ativado(s)" if active else "desativado(s)"
    if changed:
        messages.success(request, f"{changed} flow(s) {verb}.")
    if skipped:
        messages.info(request, f"{skipped} já estava(m) no estado desejado — ignorado(s).")
    if errors:
        messages.error(request, "Falha em: " + "; ".join(errors))


@admin.register(DisabledFlowSchedule)
class DisabledFlowScheduleAdmin(admin.ModelAdmin):
    list_display = [
        "flow_name_display",
        "tables_display",
        "deployment_id",
        "disabled_at",
        "is_schedule_active",
        "reactivated_at",
    ]
    # flow_name_display already renders its own <a> to the change page. Must be
    # None, not [] — Django treats [] as "unset" and falls back to
    # auto-linking the first column, nesting an <a> around it either way.
    list_display_links = None
    # Checkbox editable straight from the list, for a quick single/couple-row
    # toggle without opening the change page. Goes through save_model() below,
    # same as the change form — Prefect gets called exactly the same way.
    # confirm_schedule_toggle.js (Media, below) asks for confirmation and
    # auto-submits on "yes" instead of waiting for a separate "Save" click.
    list_editable = ["is_schedule_active"]
    list_filter = ["is_schedule_active"]
    search_fields = ["flow_name"]
    actions = [activate_selected, deactivate_selected]
    readonly_fields = [
        "flow_name_display",
        "tables_display",
        "deployment_id",
        "disabled_at",
        "reactivated_at",
    ]

    class Media:
        js = ["admin_data_tools/js/confirm_schedule_toggle.js"]
        css = {"all": ["admin_data_tools/css/hide_manual_save_button.css"]}

    fields = [
        "flow_name_display",
        "tables_display",
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
            '<a href="{}" target="_blank" rel="noopener" '
            'class="btn btn-secondary btn-sm" style="padding: 1px 6px;">Prefect ↗</a> - '
            '<a href="{}">{}</a>',
            deployment_url,
            change_url,
            obj.flow_name,
        )

    flow_name_display.short_description = "Flow Name"
    flow_name_display.admin_order_field = "flow_name"

    def tables_display(self, obj):
        """Render the tables this flow feeds, each linking to its change page.

        Args:
            obj: The ``DisabledFlowSchedule`` instance being displayed.

        Returns:
            Comma-separated links to each table's admin change page, or an em
            dash if none are linked.
        """
        tables = list(obj.tables.all())
        if not tables:
            return "—"

        def change_url(table):
            return reverse(
                f"admin:{table._meta.app_label}_{table._meta.model_name}_change",
                args=[table.pk],
            )

        return format_html_join(
            ", ", '<a href="{}">{}</a>', ((change_url(table), str(table)) for table in tables)
        )

    tables_display.short_description = "Tables"

    def save_model(self, request, obj, form, change):
        if change and "is_schedule_active" in form.changed_data:
            apply_schedule_state(obj, obj.is_schedule_active)

        super().save_model(request, obj, form, change)
