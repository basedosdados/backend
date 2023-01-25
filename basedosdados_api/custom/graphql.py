# -*- coding: utf-8 -*-
"""
Utilities for building auto-generated GraphQL schemas. Primarily based on
https://github.com/timothyjlaurent/auto-graphene-django
"""

# TODO:
# - Query: Add filtering by many-to-many fields
# - Mutation: Remove mandatory "ID" field from "...MutationPayload"
# - Mutation: Add support for many-to-many fields

from django.apps import apps
from django.contrib.postgres.fields import ArrayField, JSONField
from django.db import models
from django.forms import ModelForm
from graphene import relay, ObjectType, Schema, UUID
from graphene_django import DjangoObjectType
from graphene_django.forms.mutation import DjangoModelFormMutation
from graphene_django.filter import DjangoFilterConnectionField


class PlainTextNode(relay.Node):
    class Meta:
        name = "Node"

    @staticmethod
    def to_global_id(type, id):
        return "{}:{}".format(type, id)

    @staticmethod
    def from_global_id(global_id):
        return global_id.split(":")


def id_resolver(self, *_):
    return self.id


def generate_filter_fields(model: models.Model):
    exempted_field_types = (
        ArrayField,
        JSONField,
        models.ManyToOneRel,
    )
    exempted_field_names = ("_field_status",)
    string_field_types = (models.CharField, models.TextField)
    comparable_field_types = (
        models.IntegerField,
        models.FloatField,
        models.DecimalField,
        models.DateTimeField,
        models.DateField,
        models.TimeField,
        models.DurationField,
    )
    foreign_key_field_types = (models.ForeignKey,)

    def _get_filter_fields(model: models.Model):
        filter_fields = {}
        model_fields = model._meta.get_fields()
        for field in model_fields:
            if (
                isinstance(field, exempted_field_types)
                or field.name in exempted_field_names
            ):
                continue
            if isinstance(field, foreign_key_field_types):
                related_model: models.Model = field.related_model
                related_model_filter_fields = _get_filter_fields(related_model)
                for (
                    related_model_field_name,
                    related_model_field_filter,
                ) in related_model_filter_fields.items():
                    filter_fields[
                        f"{field.name}__{related_model_field_name}"
                    ] = related_model_field_filter
                continue
            filter_fields[field.name] = ["exact"]
            if isinstance(field, string_field_types):
                filter_fields[field.name] += ["icontains", "istartswith", "iendswith"]
            elif isinstance(field, comparable_field_types):
                filter_fields[field.name] += ["lt", "lte", "gt", "gte"]
        return filter_fields

    return _get_filter_fields(model)


def create_model_object_meta(model: models.Model):
    return type(
        "Meta",
        (object,),
        dict(
            model=(model),
            interfaces=((PlainTextNode,)),
            filter_fields=(generate_filter_fields(model)),
            # filter_order_by=True,
        ),
    )


def generate_model_object_type(model: models.Model):
    meta = type(
        "Meta",
        (object,),
        dict(
            model=(model),
        ),
    )
    return type(
        f"{model.__name__}Type",
        (DjangoObjectType,),
        dict(
            Meta=meta,
            _id=UUID(name="_id"),
            resolve__id=id_resolver,
        ),
    )


def generate_form_fields(model: models.Model):
    whitelist_field_types = (
        models.DateTimeField,
        models.SlugField,
        models.CharField,
        models.URLField,
        models.ForeignKey,
        models.TextField,
        models.BooleanField,
        models.BigIntegerField,
    )
    blacklist_field_names = (
        "_field_status",
        "id",
        "created_at",
        "updated_at",
    )
    fields = []
    for field in model._meta.get_fields():
        if (
            isinstance(field, whitelist_field_types)
            and field.name not in blacklist_field_names
        ):
            fields.append(field.name)
    return fields


def generate_form(model: models.Model):
    meta = type(
        "Meta",
        (object,),
        dict(
            model=(model),
            fields=(generate_form_fields(model)),
        ),
    )
    return type(f"{model.__name__}Form", (ModelForm,), dict(Meta=meta))


def build_query_objs(application_name: str):
    queries = {}
    models = apps.get_app_config(application_name).get_models()

    for model in models:
        model_name = model.__name__
        meta_class = create_model_object_meta(model)

        node = type(
            f"{model_name}Node",
            (DjangoObjectType,),
            dict(
                Meta=meta_class,
                _id=UUID(name="_id"),
                resolve__id=id_resolver,
            ),
        )
        queries.update({f"{model_name}Node": PlainTextNode.Field(node)})
        queries.update({f"all_{model_name}": DjangoFilterConnectionField(node)})
    return queries


def build_mutation_objs(application_name: str):
    mutations = {}
    models = apps.get_app_config(application_name).get_models()

    for model in models:
        model_name = model.__name__

        mutation = type(
            f"{model_name}Mutation",
            (DjangoModelFormMutation,),
            {
                model_name.lower(): PlainTextNode.Field(
                    generate_model_object_type(model)
                ),
                "Meta": type(
                    "Meta",
                    (object,),
                    dict(
                        form_class=(generate_form(model)),
                    ),
                ),
            },
        )
        mutations.update({f"{model_name}Mutation": mutation.Field()})
    return mutations


def build_query_schema(application_name: str):
    query = type("Query", (ObjectType,), build_query_objs(application_name))
    return query


def build_mutation_schema(application_name: str):
    mutation = type("Mutation", (ObjectType,), build_mutation_objs(application_name))
    return mutation


def build_schema(application_name: str):
    query = build_query_schema(application_name)
    mutation = build_mutation_schema(application_name)
    return Schema(query=query, mutation=mutation)
