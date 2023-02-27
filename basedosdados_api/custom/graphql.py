# -*- coding: utf-8 -*-
"""
Utilities for building auto-generated GraphQL schemas. Primarily based on
https://github.com/timothyjlaurent/auto-graphene-django
"""
from copy import deepcopy
from typing import Iterable, Optional

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import models
from django.forms.fields import FileField
from django.forms import ModelForm, modelform_factory
from graphene import Boolean, List, Mutation, ObjectType, relay, Schema, String, UUID
from graphene_django import DjangoObjectType
from graphene_django.forms.mutation import DjangoModelFormMutation
from graphene_django.filter import DjangoFilterConnectionField
import graphql_jwt
from graphql_jwt.decorators import login_required


class PlainTextNode(relay.Node):
    class Meta:
        name = "Node"

    @staticmethod
    def to_global_id(type, id):
        return "{}:{}".format(type, id)

    @staticmethod
    def from_global_id(global_id):
        return global_id.split(":")


class CustomModelForm(ModelForm):
    def __init__(self, *args, **kwargs) -> None:
        data = args[0] if args else kwargs.get("data")
        # Store raw data so we can verify whether the user has filled None or hasn't filled anything
        self.__raw_data = deepcopy(data)
        super().__init__(*args, **kwargs)
        # Store which fields are required so we can validate them later
        self.__required_fields = set()
        for field_name, field in self.fields.items():
            if field.required:
                self.__required_fields.add(field_name)
            field.required = False

    def _clean_fields(self):
        id_provided: bool = self.__raw_data.get("id") is not None
        for name, bf in self._bound_items():
            field = bf.field
            value = bf.initial
            if name in self.__raw_data:
                value = self.__raw_data[name]
            if value is None and name in self.__required_fields and not id_provided:
                self.add_error(
                    name,
                    ValidationError(field.error_messages["required"], code="required"),
                )
                continue
            try:
                if isinstance(field, FileField):
                    value = field.clean(value, bf.initial)
                else:
                    value = field.clean(value)
                self.cleaned_data[name] = value
                if hasattr(self, "clean_%s" % name):
                    value = getattr(self, "clean_%s" % name)()
                    self.cleaned_data[name] = value
            except ValidationError as e:
                self.add_error(name, e)


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
            "mutate_and_get_payload": classmethod(
                login_required(
                    lambda cls, root, info, **input: super(
                        cls, cls
                    ).mutate_and_get_payload(root, info, **input)
                )
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
            "mutate": classmethod(login_required(mutate)),
        },
    )


def id_resolver(self, *_):
    return self.id


def generate_filter_fields(model: models.Model):
    exempted_field_types = ()
    exempted_field_names = ("_field_status",)
    string_field_types = (models.CharField, models.TextField)
    comparable_field_types = (
        models.BigIntegerField,
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
        models.OneToOneRel,
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
        foreign_models = [
            f.related_model
            for f in model_fields
            if isinstance(f, foreign_key_field_types)
        ]
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
                related_model_filter_fields, _ = _get_filter_fields(
                    related_model, used_models=used_models + foreign_models
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
        models.IntegerField,
        models.OneToOneField,
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
    return modelform_factory(
        model, form=CustomModelForm, fields=generate_form_fields(model)
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


def build_mutation_schema(application_name: str, add_jwt_mutations: bool = True):
    base_mutations = build_mutation_objs(application_name)
    if add_jwt_mutations:
        base_mutations.update(
            {
                "token_auth": graphql_jwt.ObtainJSONWebToken.Field(),
                "verify_token": graphql_jwt.Verify.Field(),
                "refresh_token": graphql_jwt.Refresh.Field(),
            }
        )
    mutation = type("Mutation", (ObjectType,), base_mutations)
    return mutation


def build_schema(application_name: str, add_jwt_mutations: bool = True):
    query = build_query_schema(application_name)
    mutation = build_mutation_schema(
        application_name, add_jwt_mutations=add_jwt_mutations
    )
    return Schema(query=query, mutation=mutation)
