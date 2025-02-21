# -*- coding: utf-8 -*-
from django.contrib import admin, messages

from .models import (
    Credit,
    Endpoint,
    EndpointCategory,
    EndpointParameter,
    EndpointPricingTier,
    Key,
    Request,
)


class KeyInline(admin.TabularInline):
    model = Key
    extra = 0
    readonly_fields = (
        "id",
        "name",
        "prefix",
        "is_active",
        "expires_at",
        "created_at",
        "updated_at",
    )
    fields = readonly_fields
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class EndpointParameterInline(admin.TabularInline):
    model = EndpointParameter
    extra = 0
    readonly_fields = (
        "id",
        "name",
        "description",
        "type",
        "required",
        "created_at",
        "updated_at",
        "parameter_actions",
    )
    fields = readonly_fields
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class EndpointPricingTierInline(admin.TabularInline):
    model = EndpointPricingTier
    extra = 0
    readonly_fields = (
        "id",
        "min_requests",
        "max_requests",
        "price_per_request",
        "currency",
        "created_at",
        "updated_at",
        "pricing_actions",
    )
    fields = readonly_fields
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class KeyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "account",
        "prefix",
        "balance",
        "is_active",
        "expires_at",
        "created_at",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "prefix", "account__email", "account__full_name")
    readonly_fields = ("id", "prefix", "hash", "balance", "created_at", "updated_at")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "account",
                    "prefix",
                    "balance",
                    "is_active",
                    "expires_at",
                )
            },
        ),
    )
    ordering = ["-created_at"]

    def has_add_permission(self, request):
        return True

    def save_model(self, request, obj, form, change):
        if not change:  # Only when creating new object
            obj, key = Key.create_key(**form.cleaned_data)
            messages.success(
                request,
                f"API Key generated successfully. "
                f"Please copy this key now as it won't be shown again: {key}",
            )
        else:
            super().save_model(request, obj, form, change)


class EndpointCategoryAdmin(admin.ModelAdmin):
    list_display = ("slug", "name", "description")
    list_filter = ("slug", "name", "description")
    search_fields = ("slug", "name", "description")
    readonly_fields = ("id", "created_at", "updated_at")


class EndpointParameterAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "endpoint")
    list_filter = ("name", "description", "endpoint")
    search_fields = ("name", "description", "endpoint__name")
    readonly_fields = ("id", "created_at", "updated_at")


class EndpointPricingTierAdmin(admin.ModelAdmin):
    list_display = ("endpoint", "min_requests", "max_requests", "price_per_request")
    list_filter = ("endpoint", "min_requests", "max_requests", "price_per_request")
    search_fields = ("endpoint__name", "min_requests", "max_requests", "price_per_request")
    readonly_fields = ("id", "created_at", "updated_at")


class EndpointAdmin(admin.ModelAdmin):
    list_display = ("slug", "name", "description", "category")
    list_filter = ("slug", "name", "description", "category")
    search_fields = ("slug", "name", "description", "category__name")
    readonly_fields = ("id", "created_at", "updated_at", "full_slug", "full_name")
    inlines = [EndpointParameterInline, EndpointPricingTierInline]


class CreditAdmin(admin.ModelAdmin):
    list_display = ("key", "amount", "currency", "created_at")
    list_filter = ("key", "currency")
    search_fields = ("key__name", "currency__name")
    readonly_fields = ("id", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class RequestAdmin(admin.ModelAdmin):
    list_display = ("key", "endpoint", "created_at")
    list_filter = ("key", "endpoint")
    search_fields = ("key__name", "endpoint__name")
    readonly_fields = ("id", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Key, KeyAdmin)
admin.site.register(Endpoint, EndpointAdmin)
admin.site.register(EndpointCategory, EndpointCategoryAdmin)
admin.site.register(EndpointParameter, EndpointParameterAdmin)
admin.site.register(EndpointPricingTier, EndpointPricingTierAdmin)
admin.site.register(Credit, CreditAdmin)
admin.site.register(Request, RequestAdmin)
