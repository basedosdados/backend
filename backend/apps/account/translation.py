# -*- coding: utf-8 -*-
from modeltranslation.translator import TranslationOptions, translator

from .models import Account, Role, Team


class TeamTranslationOptions(TranslationOptions):
    fields = ("name", "description")


class RoleTranslationOptions(TranslationOptions):
    fields = ("name", "description")


class AccountTranslationOptions(TranslationOptions):
    fields = ("description",)


translator.register(Account, AccountTranslationOptions)
translator.register(Team, TeamTranslationOptions)
translator.register(Role, RoleTranslationOptions)
