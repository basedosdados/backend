# -*- coding: utf-8 -*-
from django.contrib import admin

from basedosdados_api.account.models import RegistrationToken, Team, Role, Profile

admin.site.register(RegistrationToken)
admin.site.register(Team)
admin.site.register(Role)
admin.site.register(Profile)
