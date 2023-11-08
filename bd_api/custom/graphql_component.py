# -*- coding: utf-8 -*-
from graphene import Connection, Int, Scalar, relay


class FileFieldScalar(Scalar):
    @staticmethod
    def serialize(value):
        if not value:
            return ""
        return value.url

    @staticmethod
    def parse_literal(node):
        return node

    @staticmethod
    def parse_value(value):
        return value


class PlainTextNode(relay.Node):
    class Meta:
        name = "Node"

    @staticmethod
    def to_global_id(type, id):
        return "{}:{}".format(type, id)

    @staticmethod
    def from_global_id(global_id):
        return global_id.split(":")


class CountableConnection(Connection):
    class Meta:
        abstract = True

    total_count = Int()
    edge_count = Int()

    def resolve_total_count(self, info, **kwargs):
        return self.length

    def resolve_edge_count(self, info, **kwargs):
        return len(self.edges)
