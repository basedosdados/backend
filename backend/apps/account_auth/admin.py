# -*- coding: utf-8 -*-
from django import forms
from django.contrib import admin, messages

from backend.apps.account_auth.models import (
    SCOPE_CHOICES,
    Access,
    BackendToken,
    Domain,
    Token,
)


class AccessInline(admin.TabularInline):
    model = Access


class DomainAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "is_active")
    inlines = [AccessInline]


class TokenAdmin(admin.ModelAdmin):
    list_display = ("user", "domain", "is_active")
    inlines = [AccessInline]


class AccessAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "success", "domain")


admin.site.register(Domain, DomainAdmin)
admin.site.register(Token, TokenAdmin)
admin.site.register(Access, AccessAdmin)


# ---------------------------------------------------------------------------
# BackendToken admin
# ---------------------------------------------------------------------------

_SCOPE_WIDGET_CHOICES = [(s, s) for s in SCOPE_CHOICES]


class BackendTokenAdminForm(forms.ModelForm):
    scopes = forms.MultipleChoiceField(
        choices=_SCOPE_WIDGET_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = BackendToken
        fields = "__all__"

    def clean_scopes(self):
        return list(self.cleaned_data.get("scopes", []))


class BackendTokenAdmin(admin.ModelAdmin):
    form = BackendTokenAdminForm
    list_display = ("user", "name", "prefix", "scopes", "expires_at", "last_used_at", "is_active")
    list_filter = ("is_active",)
    readonly_fields = ("prefix", "hashed_key", "created_at", "last_used_at")
    search_fields = ("user__email", "name")

    def save_model(self, request, obj, form, change):
        from backend.apps.account_auth.mutations import _generate_raw_token, _hash_token

        if not change:
            raw = _generate_raw_token()
            obj.prefix = raw[len("bdtoken_") : len("bdtoken_") + 8]
            obj.hashed_key = _hash_token(raw)
            super().save_model(request, obj, form, change)
            self.message_user(
                request,
                f"Token created: {raw} — copy now, it will not be shown again.",
                level=messages.WARNING,
            )
        else:
            super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj:
            form.base_fields["scopes"].initial = obj.scopes
        return form


admin.site.register(BackendToken, BackendTokenAdmin)
