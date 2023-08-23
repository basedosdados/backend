# -*- coding: utf-8 -*-
from modeltranslation.translator import TranslationOptions, translator

from .models import Account


class AccountTranslationOptions(TranslationOptions):
    fields = ("description",)


translator.register(Account, AccountTranslationOptions)
