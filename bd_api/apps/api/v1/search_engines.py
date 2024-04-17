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
            "ngram": {
                "tokenizer": "ngram",
                "filter": ["asciifolding", "lowercase"],
            },
            "edgengram": {
                "tokenizer": "edgengram",
                "filter": ["asciifolding", "lowercase"],
            },
            "snowball_en": {
                "type": "snowball",
                "language": "English",
                "filter": ["asciifolding"],
            },
            "snowball_pt": {
                "type": "snowball",
                "language": "Portuguese",
                "filter": ["asciifolding"],
            },
        }
        tokenizer = {
            "ngram": {
                "type": "ngram",
                "min_gram": 3,
                "max_gram": 3,
                "token_chars": ["letter", "digit"],
            },
            "edgengram": {
                "type": "edge_ngram",
                "min_gram": 3,
                "max_gram": 15,
                "token_chars": ["letter", "digit"],
            },
        }
        self.DEFAULT_SETTINGS["settings"]["analysis"]["analyzer"] = analyzer
        self.DEFAULT_SETTINGS["settings"]["analysis"]["tokenizer"] = tokenizer

    def build_schema(self, fields):
        content_field_name, mapping = super().build_schema(fields)
        for field_class in fields.values():
            field_mapping = mapping[field_class.index_fieldname]
            if field_mapping["type"] == "text" and field_class.indexed:
                if not hasattr(field_class, "facet_for"):
                    if field_class.field_type not in ("ngram", "edge_ngram"):
                        field_mapping["analyzer"] = "ngram"
                        field_mapping["fields"] = {
                            "edgengram": {"type": "text", "analyzer": "edgengram"},
                            "snowball_pt": {"type": "text", "analyzer": "snowball_pt"},
                            "snowball_en": {"type": "text", "analyzer": "snowball_en"},
                        }
            mapping.update({field_class.index_fieldname: field_mapping})
        return (content_field_name, mapping)


class AsciifoldingElasticSearchEngine(es_backend.Elasticsearch7SearchEngine):
    backend = ASCIIFoldingElasticBackend
