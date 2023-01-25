# -*- coding: utf-8 -*-
"""
Utilities for building auto-generated GraphQL schemas. Primarily based on
https://github.com/timothyjlaurent/auto-graphene-django
"""

# TODO:
# - Add filtering by foreign key fields
# - Add filtering by many-to-many fields
# - Add mutations

from django.apps import apps
from django.contrib.postgres.fields import ArrayField, JSONField
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models
from graphene import relay, ObjectType, UUID
from graphene_django import DjangoObjectType
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


def generate_filter_fields(model):
    exempted_field_types = (
        ArrayField,
        GenericForeignKey,
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
    filter_fields = {}
    for field in model._meta.get_fields():
        if (
            isinstance(field, exempted_field_types)
            or field.name in exempted_field_names
        ):
            continue
        filter_fields[field.name] = ["exact"]
        if isinstance(field, string_field_types):
            filter_fields[field.name] += ["icontains", "istartswith", "iendswith"]
        elif isinstance(field, comparable_field_types):
            filter_fields[field.name] += ["lt", "lte", "gt", "gte"]
    return filter_fields


def create_model_object_meta(model):
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


def build_query_schema(application_name: str):
    query = type("Query", (ObjectType,), build_query_objs(application_name))
    return query
