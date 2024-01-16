# -*- coding: utf-8 -*-
from typing import List

from django.db import models


class BaseModel(models.Model):
    """
    An abstract base class model that provides whitelist
    of fields to be used for filtering in the GraphQL API
    """

    class Meta:
        abstract = True

    graphql_filter_fields_whitelist: List[str] = None
    graphql_filter_fields_blacklist: List[str] = []
    graphql_nested_filter_fields_whitelist: List[str] = None
    graphql_nested_filter_fields_blacklist: List[str] = []

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
