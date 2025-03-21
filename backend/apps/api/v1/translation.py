# -*- coding: utf-8 -*-
from modeltranslation.translator import TranslationOptions, translator

from .models import (
    Analysis,
    AnalysisType,
    Area,
    Availability,
    Column,
    ColumnOriginalName,
    Dataset,
    Entity,
    EntityCategory,
    InformationRequest,
    Language,
    License,
    MeasurementUnit,
    MeasurementUnitCategory,
    Organization,
    QualityCheck,
    RawDataSource,
    Status,
    Table,
    Tag,
    Theme,
)


class AnalysisTranslationOptions(TranslationOptions):
    fields = (
        "name",
        "description",
    )


class AnalysisTypeTranslationOptions(TranslationOptions):
    fields = ("name",)


class AreaTranslationOptions(TranslationOptions):
    fields = ("name",)


class AvailabilityTranslationOptions(TranslationOptions):
    fields = ("name",)


class ColumnTranslationOptions(TranslationOptions):
    fields = ("name", "name_staging", "description", "observations")


class ColumnOriginalNameTranslationOptions(TranslationOptions):
    fields = ("name",)


class DatasetTranslationOptions(TranslationOptions):
    fields = ("name", "description")


class EntityTranslationOptions(TranslationOptions):
    fields = ("name",)


class EntityCategoryTranslationOptions(TranslationOptions):
    fields = ("name",)


class InformationRequestTranslationOptions(TranslationOptions):
    fields = ("observations",)


class LanguageTranslationOptions(TranslationOptions):
    fields = ("name",)


class LicenseTranslationOptions(TranslationOptions):
    fields = ("name",)


class MeasurementUnitTranslationOptions(TranslationOptions):
    fields = ("name",)


class MeasurementUnitCategoryTranslationOptions(TranslationOptions):
    fields = ("name",)


class OrganizationTranslationOptions(TranslationOptions):
    fields = ("name", "description")


class QualityCheckTranslationOptions(TranslationOptions):
    fields = (
        "name",
        "description",
    )


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


translator.register(Analysis, AnalysisTranslationOptions)
translator.register(AnalysisType, AnalysisTypeTranslationOptions)
translator.register(Area, AreaTranslationOptions)
translator.register(Availability, AvailabilityTranslationOptions)
translator.register(Column, ColumnTranslationOptions)
translator.register(ColumnOriginalName, ColumnOriginalNameTranslationOptions)
translator.register(Dataset, DatasetTranslationOptions)
translator.register(Entity, EntityTranslationOptions)
translator.register(EntityCategory, EntityCategoryTranslationOptions)
translator.register(InformationRequest, InformationRequestTranslationOptions)
translator.register(Language, LanguageTranslationOptions)
translator.register(License, LicenseTranslationOptions)
translator.register(MeasurementUnit, MeasurementUnitTranslationOptions)
translator.register(MeasurementUnitCategory, MeasurementUnitCategoryTranslationOptions)
translator.register(Organization, OrganizationTranslationOptions)
translator.register(QualityCheck, QualityCheckTranslationOptions)
translator.register(RawDataSource, RawDataSourceTranslationOptions)
translator.register(Status, StatusTranslationOptions)
translator.register(Table, TableTranslationOptions)
translator.register(Tag, TagTranslationOptions)
translator.register(Theme, ThemeTranslationOptions)
