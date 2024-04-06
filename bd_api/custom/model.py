# -*- coding: utf-8 -*-
from typing import Callable, List

from django.conf import settings
from django.db import models
from django.urls import reverse
from graphql_jwt.decorators import staff_member_required

from bd_api.custom.graphql_jwt import anyone_required

default_blacklist_fields = [
    "created_at",
    "updated_at",
    "deleted_at",
    "pk",
    "id",
    "order",
    "_field_status",
]
default_query_decorator = anyone_required
default_mutation_decorator = staff_member_required


class BaseModel(models.Model):
    """Abstract base class model that provides whitelist
    of fields to be used for filtering in the GraphQL API

    Attributes:
    - graphql_visible: show or hide the model in the documentation
    - graphql_fields_black_list: list of fields to hide in mutations
    - graphql_query_decorator: authentication decorator for queries
    - graphql_mutation_decorator: authentication decorator for mutations
    """

    class Meta:
        abstract = True

    graphql_visible: bool = True

    graphql_fields_whitelist: List[str] = []
    graphql_fields_blacklist: List[str] = default_blacklist_fields
    graphql_filter_fields_whitelist: List[str] = []
    graphql_filter_fields_blacklist: List[str] = []
    graphql_nested_filter_fields_whitelist: List[str] = []
    graphql_nested_filter_fields_blacklist: List[str] = []

    graphql_query_decorator: Callable = default_query_decorator
    graphql_mutation_decorator: Callable = default_mutation_decorator

    @classmethod
    def get_graphql_filter_fields_whitelist(cls) -> List[models.Field]:
        """
        Returns a list of fields that can be used for filtering in the GraphQL API.

        If the class attribute `graphql_filter_fields_whitelist` is set, it will
        be used.
        Otherwise, if there are field names in `graphql_filter_fields_blacklist`,
        all fields will be used except those in the blacklist.
        Otherwise, all fields will be used.
        """
        if cls.graphql_filter_fields_whitelist:
            field_names = cls.graphql_filter_fields_whitelist
            return [f for f in cls._meta.get_fields() if f.name in field_names]
        if cls.graphql_filter_fields_blacklist:
            return [
                f
                for f in cls._meta.get_fields()
                if f.name not in cls.graphql_filter_fields_blacklist
            ]
        return cls._meta.get_fields()

    @classmethod
    def get_graphql_nested_filter_fields_whitelist(cls) -> List[models.Field]:
        """
        Returns a list of fields that can be used for nested filtering in the GraphQL API.

        If the class attribute `graphql_nested_filter_fields_whitelist` is set, it will
        be used.
        Otherwise, if there are field names in `graphql_nested_filter_fields_blacklist`,
        all fields will be used except those in the blacklist.
        Otherwise, all fields will be used.
        """
        if cls.graphql_nested_filter_fields_whitelist:
            field_names = cls.graphql_nested_filter_fields_whitelist
            return [f for f in cls._meta.get_fields() if f.name in field_names]
        if cls.graphql_nested_filter_fields_blacklist:
            return [
                f
                for f in cls._meta.get_fields()
                if f.name not in cls.graphql_nested_filter_fields_blacklist
            ]
        return cls._meta.get_fields()

    @property
    def admin_url(self):
        viewname = f"admin:{self._meta.app_label}_{self._meta.model_name}_change"
        endpoint = reverse(viewname, kwargs={"object_id": self.pk})
        return f"{settings.BACKEND_URL}{endpoint}"
