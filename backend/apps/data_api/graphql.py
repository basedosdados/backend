# -*- coding: utf-8 -*-
from graphene import ObjectType
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField

from backend.apps.data_api.models import (
    Credit,
    Endpoint,
    EndpointCategory,
    EndpointParameter,
    EndpointPricingTier,
    Key,
    Request,
)
from backend.custom.graphql_base import CountableConnection, PlainTextNode


class KeyNode(DjangoObjectType):
    class Meta:
        model = Key
        fields = "__all__"
        filter_fields = {
            "id": ["exact"],
            "name": ["exact", "icontains"],
            "is_active": ["exact"],
        }
        interfaces = (PlainTextNode,)
        connection_class = CountableConnection


class EndpointNode(DjangoObjectType):
    class Meta:
        model = Endpoint
        fields = "__all__"
        filter_fields = {
            "id": ["exact"],
            "slug": ["exact", "icontains"],
            "name": ["exact", "icontains"],
            "is_active": ["exact"],
            "is_deprecated": ["exact"],
        }
        interfaces = (PlainTextNode,)
        connection_class = CountableConnection


class EndpointCategoryNode(DjangoObjectType):
    class Meta:
        model = EndpointCategory
        fields = "__all__"
        filter_fields = {
            "id": ["exact"],
            "slug": ["exact", "icontains"],
            "name": ["exact", "icontains"],
        }
        interfaces = (PlainTextNode,)
        connection_class = CountableConnection


class EndpointParameterNode(DjangoObjectType):
    class Meta:
        model = EndpointParameter
        fields = "__all__"
        filter_fields = {
            "id": ["exact"],
            "name": ["exact", "icontains"],
            "required": ["exact"],
            "type": ["exact"],
        }
        interfaces = (PlainTextNode,)
        connection_class = CountableConnection


class EndpointPricingTierNode(DjangoObjectType):
    class Meta:
        model = EndpointPricingTier
        fields = "__all__"
        filter_fields = {
            "id": ["exact"],
            "name": ["exact", "icontains"],
            "price": ["exact", "lt", "lte", "gt", "gte"],
            "is_active": ["exact"],
        }
        interfaces = (PlainTextNode,)
        connection_class = CountableConnection


class RequestNode(DjangoObjectType):
    class Meta:
        model = Request
        fields = "__all__"
        filter_fields = {
            "id": ["exact"],
            "status": ["exact"],
            "created_at": ["exact", "lt", "lte", "gt", "gte"],
        }
        interfaces = (PlainTextNode,)
        connection_class = CountableConnection


class CreditNode(DjangoObjectType):
    class Meta:
        model = Credit
        fields = "__all__"
        filter_fields = {
            "id": ["exact"],
            "amount": ["exact", "lt", "lte", "gt", "gte"],
            "created_at": ["exact", "lt", "lte", "gt", "gte"],
        }
        interfaces = (PlainTextNode,)
        connection_class = CountableConnection


class Query(ObjectType):
    key = PlainTextNode.Field(KeyNode)
    all_keys = DjangoFilterConnectionField(KeyNode)

    endpoint = PlainTextNode.Field(EndpointNode)
    all_endpoints = DjangoFilterConnectionField(EndpointNode)

    endpoint_category = PlainTextNode.Field(EndpointCategoryNode)
    all_endpoint_categories = DjangoFilterConnectionField(EndpointCategoryNode)

    endpoint_parameter = PlainTextNode.Field(EndpointParameterNode)
    all_endpoint_parameters = DjangoFilterConnectionField(EndpointParameterNode)

    endpoint_pricing_tier = PlainTextNode.Field(EndpointPricingTierNode)
    all_endpoint_pricing_tiers = DjangoFilterConnectionField(EndpointPricingTierNode)

    request = PlainTextNode.Field(RequestNode)
    all_requests = DjangoFilterConnectionField(RequestNode)

    credit = PlainTextNode.Field(CreditNode)
    all_credits = DjangoFilterConnectionField(CreditNode)
