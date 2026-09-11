# -*- coding: utf-8 -*-

from modeltranslation.translator import TranslationOptions, translator

from .models import Endpoint, EndpointCategory, EndpointParameter


class EndpointTranslationOptions(TranslationOptions):
    fields = ("name", "description")


class EndpointParameterTranslationOptions(TranslationOptions):
    fields = ("name", "description")


class EndpointCategoryTranslationOptions(TranslationOptions):
    fields = ("name", "description")


translator.register(Endpoint, EndpointTranslationOptions)
translator.register(EndpointParameter, EndpointParameterTranslationOptions)
translator.register(EndpointCategory, EndpointCategoryTranslationOptions)
