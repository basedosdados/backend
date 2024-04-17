# -*- coding: utf-8 -*-
"""
Utilities for building auto-generated GraphQL schemas.
https://github.com/timothyjlaurent/auto-graphene-django
"""

from collections import OrderedDict
from copy import deepcopy
from functools import partial
from typing import Iterable, Optional, get_type_hints

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import models
from django.forms import ModelForm, modelform_factory
from django.forms import fields as forms_fields
from graphene import (
    ID,
    UUID,
    Boolean,
    Field,
    InputField,
    Int,
    List,
    Mutation,
    ObjectType,
    Schema,
    String,
)
from graphene.types.generic import GenericScalar
from graphene.types.utils import yank_fields_from_attrs
from graphene_django import DjangoObjectType
from graphene_django.converter import convert_django_field
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.forms.mutation import (
    DjangoModelDjangoFormMutationOptions,
    DjangoModelFormMutation,
    convert_form_field,
)
from graphene_django.registry import get_global_registry
from graphene_file_upload.scalars import Upload
from graphql_jwt import ObtainJSONWebToken, Refresh, Verify

from bd_api.custom.graphql_base import CountableConnection, FileFieldScalar, PlainTextNode
from bd_api.custom.graphql_jwt import ObtainJSONWebTokenWithUser
from bd_api.custom.model import BaseModel


def build_schema(applications: list[str], extra_queries=[], extra_mutations=[]):
    queries = [build_query_schema(app) for app in applications] + extra_queries
    mutations = [build_mutation_schema(app) for app in applications] + extra_mutations

    Query = type("Query", tuple(queries), {})
    Mutation = type("Mutation", tuple(mutations), {})

    schema = Schema(query=Query, mutation=Mutation)
    return schema


### Query #####################################################################


def build_query_schema(application_name: str):
    query = type("Query", (ObjectType,), build_query_objs(application_name))
    return query


def build_query_objs(application_name: str):
    queries = {}
    models = apps.get_app_config(application_name).get_models()
    models = [m for m in models if getattr(m, "graphql_visible", False)]

    for model in models:
        model_name = model.__name__
        meta = create_model_object_meta(model)
        attr = dict(
            Meta=meta,
            _id=UUID(name="_id"),
            resolve__id=lambda self, _: self.id,
        )
        attr = build_custom_attrs(model, attr)
        node = create_node_factory(model, attr)
        queries.update({f"{model_name}Node": PlainTextNode.Field(node)})
        queries.update({f"all_{model_name}": DjangoFilterConnectionField(node)})
    return queries


def create_model_object_meta(model: BaseModel):
    return type(
        "Meta",
        (object,),
        dict(
            model=(model),
            interfaces=((PlainTextNode,)),
            connection_class=CountableConnection,
            filter_fields=(generate_filter_fields(model)),
        ),
    )


def generate_filter_fields(model: BaseModel):
    exempted_field_names = ("_field_status",)
    exempted_field_types = (
        models.ImageField,
        models.JSONField,
    )
    string_field_types = (
        models.CharField,
        models.TextField,
    )
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

    def get_filter_fields(
        model: models.Model, processed_models: Optional[Iterable[models.Model]] = None
    ):
        if processed_models is None:
            processed_models = []
        if len(processed_models) > 10:
            return {}, processed_models

        if not issubclass(model, BaseModel):
            model_fields = model._meta.get_fields()
        if issubclass(model, BaseModel) and not processed_models:
            model_fields = model.get_graphql_filter_fields_whitelist()
        if issubclass(model, BaseModel) and len(processed_models):
            model_fields = model.get_graphql_nested_filter_fields_whitelist()

        processed_models.append(model)
        filter_fields = {"id": ["exact", "isnull", "in"]}

        foreign_models = []
        for field in model_fields:
            if isinstance(field, foreign_key_field_types):
                foreign_models.append(field.related_model)

        for field in model_fields:
            if (
                False
                or "djstripe" in field.name
                or field.name in exempted_field_names
                or model.__module__.startswith("django")
                or isinstance(field, exempted_field_types)
            ):
                continue
            filter_fields[field.name] = ["exact", "isnull", "in"]
            if isinstance(field, string_field_types):
                filter_fields[field.name] += ["icontains", "istartswith", "iendswith"]
            if isinstance(field, comparable_field_types):
                filter_fields[field.name] += ["lt", "lte", "gt", "gte", "range"]
            if isinstance(field, foreign_key_field_types):
                filter_fields[field.name] = []
                if field.related_model in processed_models:
                    continue
                related_model_filter_fields, _ = get_filter_fields(
                    field.related_model,
                    processed_models,
                )
                for (
                    related_model_field_name,
                    related_model_field_filter,
                ) in related_model_filter_fields.items():
                    name = f"{field.name}__{related_model_field_name}"
                    filter_fields[name] = related_model_field_filter
        return filter_fields, processed_models

    filter_fields, _ = get_filter_fields(model)
    return filter_fields


def build_custom_attrs(model, attrs):
    def get_type(model, attr):
        """Get type of an attribute of a class"""
        try:
            func = getattr(model, attr)
            func = getattr(func, "fget")
            hint = get_type_hints(func)
            name = hint.get("return")
            return str(name)
        except Exception:
            return ""

    def match_type(model, attr):
        """Match python types to graphene types"""
        if get_type(model, attr).startswith("int"):
            return Int
        if get_type(model, attr).startswith("str"):
            return String
        if get_type(model, attr).startswith("list[int]"):
            return partial(List, of_type=Int)
        if get_type(model, attr).startswith("list[str]"):
            return partial(List, of_type=String)
        return GenericScalar

    for attr in dir(model):
        attr_func = getattr(model, attr)
        if isinstance(attr_func, property):
            if attr not in model.graphql_fields_blacklist:
                attr_type = match_type(model, attr)
                attrs.update({attr: attr_type(source=attr, description=attr_func.__doc__)})
    return attrs


def create_node_factory(model: BaseModel, attr: dict):
    """Create graphql relay node"""

    def get_queryset():
        """Create query endpoints with authorization"""

        @model.graphql_query_decorator
        def _get_queryset(cls, queryset, info):
            return super(cls, cls).get_queryset(queryset, info)

        return classmethod(_get_queryset)

    return type(
        f"{model.__name__}Node",
        (DjangoObjectType,),
        {
            **attr,
            "get_queryset": get_queryset(),
        },
    )


### Mutation ##################################################################


def build_mutation_schema(application_name: str):
    base_mutations = build_mutation_objs(application_name)
    base_mutations.update(
        {
            "token_auth": ObtainJSONWebToken.Field(),
            "auth_token": ObtainJSONWebTokenWithUser.Field(),
            "verify_token": Verify.Field(),
            "refresh_token": Refresh.Field(),
        }
    )
    mutation = type("Mutation", (ObjectType,), base_mutations)
    return mutation


def build_mutation_objs(application_name: str):
    mutations = {}
    models = apps.get_app_config(application_name).get_models()
    models = [m for m in models if getattr(m, "graphql_visible", False)]

    for model in models:
        model_name = model.__name__
        mutations.update({f"Delete{model_name}": delete_mutation_factory(model).Field()})
        mutations.update({f"CreateUpdate{model_name}": create_mutation_factory(model).Field()})
    return mutations


def create_mutation_factory(model: BaseModel):
    def mutate_and_get_payload():
        """Create mutation endpoints with authorization"""

        @model.graphql_mutation_decorator
        def _mutate(cls, root, info, **input):
            return super(cls, cls).mutate_and_get_payload(root, info, **input)

        return classmethod(_mutate)

    return type(
        f"CreateUpdate{model.__name__}",
        (CreateUpdateMutation,),
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
            "mutate_and_get_payload": mutate_and_get_payload(),
        },
    )


def delete_mutation_factory(model: BaseModel):
    def mutate():
        """Create mutation endpoints with authorization"""

        @model.graphql_mutation_decorator
        def _mutate(cls, root, info, id):
            try:
                obj = model.objects.get(pk=id)
                obj.delete()
            except model.DoesNotExist:
                return cls(ok=False, errors=["Object does not exist."])
            return cls(ok=True, errors=[])

        return classmethod(_mutate)

    if "account" in model.__name__.lower():
        _id_type = ID(required=True)
    else:
        _id_type = UUID(required=True)

    return type(
        f"Delete{model.__name__}",
        (Mutation,),
        {
            "Arguments": type(
                "Arguments",
                (object,),
                dict(
                    id=_id_type,
                ),
            ),
            "ok": Boolean(),
            "errors": List(String),
            "mutate": mutate(),
        },
    )


def generate_form(model: BaseModel):
    return modelform_factory(model, form=CustomModelForm, fields=generate_form_fields(model))


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
                if isinstance(field, forms_fields.FileField):
                    value = field.clean(value, bf.initial)
                else:
                    value = field.clean(value)
                self.cleaned_data[name] = value
                if hasattr(self, "clean_%s" % name):
                    value = getattr(self, "clean_%s" % name)()
                    self.cleaned_data[name] = value
            except ValidationError as e:
                self.add_error(name, e)


class CreateUpdateMutation(DjangoModelFormMutation):
    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(
        cls,
        form_class=None,
        model=None,
        return_field_name=None,
        only_fields=(),
        exclude_fields=(),
        **options,
    ):
        if not form_class:
            raise Exception("form_class is required for DjangoModelFormMutation")

        if not model:
            model = form_class._meta.model

        if not model:
            raise Exception("model is required for DjangoModelFormMutation")

        form = form_class()
        input_fields = fields_for_form(form, only_fields, exclude_fields)
        if "id" not in exclude_fields:
            input_fields["id"] = ID()

        registry = get_global_registry()
        model_type = registry.get_type_for_model(model)
        if not model_type:
            raise Exception("No type registered for model: {}".format(model.__name__))

        if not return_field_name:
            model_name = model.__name__
            return_field_name = model_name[:1].lower() + model_name[1:]

        output_fields = OrderedDict()
        output_fields[return_field_name] = Field(model_type)

        _meta = DjangoModelDjangoFormMutationOptions(cls)
        _meta.form_class = form_class
        _meta.model = model
        _meta.return_field_name = return_field_name
        _meta.fields = yank_fields_from_attrs(output_fields, _as=Field)

        input_fields = yank_fields_from_attrs(input_fields, _as=InputField)
        super(DjangoModelFormMutation, cls).__init_subclass_with_meta__(
            _meta=_meta, input_fields=input_fields, **options
        )

    @classmethod
    def get_form_kwargs(cls, root, info, **input):
        # Get file data
        file_fields = [
            field
            for field in cls._meta.form_class.base_fields
            if isinstance(cls._meta.form_class.base_fields[field], forms_fields.FileField)
        ]
        file_data = {}
        if file_fields:
            for field in file_fields:
                if field in input:
                    file_data[field] = input[field]

        kwargs = {"data": input, "files": file_data}

        pk = input.pop("id", None)
        if pk:
            instance = cls._meta.model._default_manager.get(pk=pk)
            kwargs["instance"] = instance

        return kwargs


def fields_for_form(form, only_fields, exclude_fields):
    fields = OrderedDict()
    for name, field in form.fields.items():
        is_excluded = name in exclude_fields
        is_not_in_only = only_fields and name not in only_fields
        if is_excluded or is_not_in_only:
            continue
        if isinstance(field, forms_fields.FileField):
            fields[name] = Upload(description=field.help_text)
        else:
            fields[name] = convert_form_field(field)
    return fields


def generate_form_fields(model: BaseModel):
    whitelist_field_types = (
        models.DateField,
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
        models.ImageField,
        models.UUIDField,
    )
    fields = []
    for field in model._meta.get_fields():
        if isinstance(field, whitelist_field_types):
            if field.name not in model.graphql_fields_blacklist:
                fields.append(field.name)
    return fields


@convert_django_field.register(models.FileField)
def convert_file_to_url(field, registry=None):
    return FileFieldScalar(description=field.help_text, required=not field.null)
