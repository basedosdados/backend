# -*- coding: utf-8 -*-
from modeltranslation.translator import translator, TranslationOptions

from .models import (
    Profile,
    Team,
    Role,
)


class ProfileTranslationOptions(TranslationOptions):
    fields = ("description",)


class TeamTranslationOptions(TranslationOptions):
    fields = (
        "name",
        "description",
    )


class RoleTranslationOptions(TranslationOptions):
    fields = (
        "name",
        "description",
    )


translator.register(Profile, ProfileTranslationOptions)
translator.register(Team, TeamTranslationOptions)
translator.register(Role, RoleTranslationOptions)
