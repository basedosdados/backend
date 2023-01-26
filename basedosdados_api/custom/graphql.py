# -*- coding: utf-8 -*-
"""
Utilities for building auto-generated GraphQL schemas. Primarily based on
https://github.com/timothyjlaurent/auto-graphene-django
"""

from typing import Iterable, Optional

from django.apps import apps
from django.db import models
from django.forms import ModelForm, modelform_factory
from graphene import Boolean, List, Mutation, ObjectType, relay, Schema, String, UUID
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


def create_mutation_factory(model: models.Model):
    return type(
        f"CreateUpdate{model.__name__}",
        (DjangoModelFormMutation,),
        {
            "Meta": type(
                "Meta",
                (object,),
                dict(
                    form_class=(generate_form(model)),
                    input_field_name="input",
                    return_field_name=model.__name__.lower(),
                ),
            ),
        },
    )


def delete_mutation_factory(model: models.Model):
    def mutate(cls, root, info, id):
        try:
            obj = model.objects.get(pk=id)
        except model.DoesNotExist:
            return cls(ok=False, errors=["Object does not exist."])
        obj.delete()
        return cls(ok=True, errors=[])

    return type(
        f"Delete{model.__name__}",
        (Mutation,),
        {
            "Arguments": type(
                "Arguments",
                (object,),
                dict(
                    id=UUID(required=True),
                ),
            ),
            "ok": Boolean(),
            "errors": List(String),
            "mutate": classmethod(mutate),
        },
    )


def id_resolver(self, *_):
    return self.id


def generate_filter_fields(model: models.Model):
    exempted_field_types = ()
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
    foreign_key_field_types = (
        models.ForeignKey,
        models.OneToOneField,
        models.ManyToManyField,
        models.ManyToManyRel,
        models.ManyToOneRel,
    )

    def _get_filter_fields(
        model: models.Model, used_models: Optional[Iterable[models.Model]] = None
    ):
        if used_models is None:
            used_models = []
        used_models.append(model)
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
                if related_model in used_models:
                    continue
                related_model_filter_fields, related_used_models = _get_filter_fields(
                    related_model, used_models=used_models
                )
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
        return filter_fields, used_models

    filter_fields, _ = _get_filter_fields(model)
    return filter_fields


def create_model_object_meta(model: models.Model):
    return type(
        "Meta",
        (object,),
        dict(
            model=(model),
            interfaces=((PlainTextNode,)),
            filter_fields=(generate_filter_fields(model)),
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
        models.ManyToManyField,
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
    return modelform_factory(model, form=ModelForm, fields=generate_form_fields(model))


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
        mutations.update(
            {f"CreateUpdate{model_name}": create_mutation_factory(model).Field()}
        )
        mutations.update(
            {f"Delete{model_name}": delete_mutation_factory(model).Field()}
        )
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
