# -*- coding: utf-8 -*-
from django.contrib import admin

from bd_api.apps.account_auth.models import (
    Access,
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
