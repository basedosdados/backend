# -*- coding: utf-8 -*-
"""
Utilities for building auto-generated GraphQL schemas. Primarily based on
https://github.com/timothyjlaurent/auto-graphene-django
"""
from copy import deepcopy
from typing import Iterable, Optional

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.forms.fields import FileField
from django.forms import ModelForm, modelform_factory
from graphene import Boolean, List, Mutation, ObjectType, relay, Schema, String, UUID, Connection, Int
from graphene_django import DjangoObjectType
from graphene_django.forms.mutation import DjangoModelFormMutation
from graphene_django.filter import DjangoFilterConnectionField
import graphql_jwt
from graphql_jwt.decorators import login_required

from basedosdados_api.custom.model import BdmModel

EXEMPTED_MODELS = ("RegistrationToken",)


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
        # Store raw data, so we can verify whether the user has filled None or hasn't filled
        # anything
        self.__raw_data = deepcopy(data)
        super().__init__(*args, **kwargs)
        # Store which fields are required, so we can validate them later
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


def create_mutation_factory(model: BdmModel):
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


def delete_mutation_factory(model: BdmModel):
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


def generate_filter_fields(model: BdmModel):
    exempted_field_types = (models.ImageField,)
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

    def is_bdm_model(model: models.Model):
        return issubclass(model, BdmModel)

    def _get_filter_fields(
        model: BdmModel, used_models: Optional[Iterable[BdmModel]] = None
    ):
        if used_models is None:
            used_models = []
            if is_bdm_model(model):
                model_fields = model.get_graphql_filter_fields_whitelist()
            else:
                model_fields = model._meta.get_fields()
        else:
            if is_bdm_model(model):
                model_fields = model.get_graphql_nested_filter_fields_whitelist()
            else:
                model_fields = model._meta.get_fields()
        used_models.append(model)
        filter_fields = {}
        foreign_models = [
            f.related_model
            for f in model_fields
            if isinstance(f, foreign_key_field_types)
        ]
        for field in model_fields:
            if (
                isinstance(field, exempted_field_types)
                or field.name in exempted_field_names
                or model.__module__.startswith("django")
            ):
                continue
            if isinstance(field, foreign_key_field_types):
                related_model: BdmModel = field.related_model
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


class CountableConnection(Connection):
    class Meta:
        abstract = True

    total_count = Int()
    edge_count = Int()

    def resolve_total_count(self, info, **kwargs):
        return self.length

    def resolve_edge_count(self, info, **kwargs):
        return len(self.edges)


def create_model_object_meta(model: BdmModel):
    return type(
        "Meta",
        (object,),
        dict(
            model=(model),
            interfaces=((PlainTextNode,)),
            filter_fields=(generate_filter_fields(model)),
            connection_class=CountableConnection,
        ),
    )


def generate_model_object_type(model: BdmModel):
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


def generate_form_fields(model: BdmModel):
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


def generate_form(model: BdmModel):
    return modelform_factory(
        model, form=CustomModelForm, fields=generate_form_fields(model)
    )


def build_query_objs(application_name: str):
    queries = {}
    models = apps.get_app_config(application_name).get_models()

    for model in models:
        model_name = model.__name__
        if model_name in EXEMPTED_MODELS:
            continue
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
        if model_name in EXEMPTED_MODELS:
            continue
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


def build_schema(application_name: list, add_jwt_mutations: bool = True):
    # schema_cache_key = f"graphql_schema_{application_name}"
    schema_cache_key = "graphql_schema_v1"
    schema_cache_dict = settings.GRAPHENE_SCHEMAS_CACHE
    # Try to fetch schema from cache
    try:
        if schema_cache_key in schema_cache_dict:
            return schema_cache_dict[schema_cache_key]
    except Exception:
        pass
    queries = [build_query_schema(app) for app in application_name]
    mutations = [
        build_mutation_schema(app, add_jwt_mutations=add_jwt_mutations)
        for app in application_name
    ]
    # query = build_query_schema(application_name)
    # mutation = build_mutation_schema(
    #     application_name, add_jwt_mutations=add_jwt_mutations
    # )

    class Query(*queries):
        pass

    class Mutations(*mutations):
        pass

    schema = Schema(query=Query, mutation=Mutations)
    # Try to cache schema
    try:
        schema_cache_dict[schema_cache_key] = schema
    except Exception:
        pass
    return schema
