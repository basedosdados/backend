# -*- coding: utf-8 -*-
from modeltranslation.translator import translator, TranslationOptions

from .models import (
    AnalysisType,
    Availability,
    Column,
    Dataset,
    Entity,
    InformationRequest,
    Language,
    License,
    Organization,
    RawDataSource,
    Status,
    Table,
    Tag,
    Theme,
    Area,
)


class AnalysisTypeTranslationOptions(TranslationOptions):
    fields = (
        "name",
        "tag",
    )


class AreaTranslationOptions(TranslationOptions):
    fields = ("name",)


class AvailabilityTranslationOptions(TranslationOptions):
    fields = ("name",)


class ColumnTranslationOptions(TranslationOptions):
    fields = ("name", "description", "observations")


class DatasetTranslationOptions(TranslationOptions):
    fields = ("name", "description")


class EntityTranslationOptions(TranslationOptions):
    fields = ("name",)


class InformationRequestTranslationOptions(TranslationOptions):
    fields = ("observations",)


class LanguageTranslationOptions(TranslationOptions):
    fields = ("name",)


class LicenseTranslationOptions(TranslationOptions):
    fields = ("name",)


class OrganizationTranslationOptions(TranslationOptions):
    fields = ("name", "description")


class RawDataSourceTranslationOptions(TranslationOptions):
    fields = (
        "name",
        "description",
    )


class StatusTranslationOptions(TranslationOptions):
    fields = ("name",)


class TableTranslationOptions(TranslationOptions):
    fields = (
        "name",
        "description",
    )


class TagTranslationOptions(TranslationOptions):
    fields = ("name",)


class ThemeTranslationOptions(TranslationOptions):
    fields = ("name",)


translator.register(AnalysisType, AnalysisTypeTranslationOptions)
translator.register(Area, AreaTranslationOptions)
translator.register(Availability, AvailabilityTranslationOptions)
translator.register(Column, ColumnTranslationOptions)
translator.register(Dataset, DatasetTranslationOptions)
translator.register(Entity, EntityTranslationOptions)
translator.register(InformationRequest, InformationRequestTranslationOptions)
translator.register(Language, LanguageTranslationOptions)
translator.register(License, LicenseTranslationOptions)
translator.register(Organization, OrganizationTranslationOptions)
translator.register(RawDataSource, RawDataSourceTranslationOptions)
translator.register(Status, StatusTranslationOptions)
translator.register(Table, TableTranslationOptions)
translator.register(Tag, TagTranslationOptions)
translator.register(Theme, ThemeTranslationOptions)
