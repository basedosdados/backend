# -*- coding: utf-8 -*-
"""
Based on the following docs:
https://gregbrown.co/code/haystack-character-folding/
https://github.com/mounirmesselmeni/MounirMesselmeni.github.io/tree/master/2015/12/13/enable-asciifolding-in-elasticsearchhaystack
"""

from abc import ABCMeta

from haystack import indexes  # noqa: F401
from haystack.backends import elasticsearch7_backend as es_backend


class ASCIIFoldingElasticBackend(es_backend.Elasticsearch7SearchBackend, metaclass=ABCMeta):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        analyzer = {
            "ascii_analyzer": {
                "type": "custom",
                "tokenizer": "standard",
                "filter": ["asciifolding", "lowercase"],
            },
            "ngram_analyzer": {
                "type": "custom",
                "tokenizer": "lowercase",
                "filter": ["asciifolding", "haystack_ngram"],
            },
            "edgengram_analyzer": {
                "type": "custom",
                "tokenizer": "lowercase",
                "filter": ["asciifolding", "haystack_edgengram"],
            },
        }
        self.DEFAULT_SETTINGS["settings"]["analysis"]["analyzer"] = analyzer

    def build_schema(self, fields):
        content_field_name, mapping = super().build_schema(fields)
        for field_class in fields.values():
            field_mapping = mapping[field_class.index_fieldname]
            if field_mapping["type"] == "text" and field_class.indexed:
                if not hasattr(field_class, "facet_for"):
                    if field_class.field_type not in ("ngram", "edge_ngram"):
                        field_mapping["analyzer"] = "ascii_analyzer"
            mapping.update({field_class.index_fieldname: field_mapping})
        return (content_field_name, mapping)


class AsciifoldingElasticSearchEngine(es_backend.Elasticsearch7SearchEngine):
    backend = ASCIIFoldingElasticBackend
