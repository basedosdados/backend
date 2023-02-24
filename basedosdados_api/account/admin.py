# -*- coding: utf-8 -*-
from django.contrib import admin
from django.contrib.auth.models import User

from basedosdados_api.account.models import RegistrationToken, Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "profile"


class UserAdmin(admin.ModelAdmin):
    inlines = (ProfileInline,)


admin.site.register(RegistrationToken)
admin.site.register(Profile)
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
