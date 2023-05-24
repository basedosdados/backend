# -*- coding: utf-8 -*-
from modeltranslation.translator import translator, TranslationOptions

from .models import (
    Account,
)


class AccountTranslationOptions(TranslationOptions):
    fields = ("description",)


translator.register(Account, AccountTranslationOptions)
