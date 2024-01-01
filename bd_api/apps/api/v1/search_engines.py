# -*- coding: utf-8 -*-
"""
Based on the following docs:
https://gregbrown.co/code/haystack-character-folding/
https://github.com/mounirmesselmeni/MounirMesselmeni.github.io/tree/master/2015/12/13/enable-asciifolding-in-elasticsearchhaystack
"""

from abc import ABCMeta

from haystack import indexes  # noqa: F401
from haystack.backends import elasticsearch7_backend as es_backend


class AsciifoldingElasticBackend(es_backend.Elasticsearch7SearchBackend, metaclass=ABCMeta):
    def __init__(self, *args, **kwargs):
        super(AsciifoldingElasticBackend, self).__init__(*args, **kwargs)
        analyzer = {
            "ascii_ngram_analyser": {
                "type": "custom",
                "tokenizer": "standard",
                "filter": ["asciifolding", "lowercase", "haystack_edgengram"],
            },
            "standard_analyzer": {
                "type": "custom",
                "tokenizer": "standard",
                "filter": ["asciifolding", "lowercase"],
            },
            "ngram_analyzer": {
                "type": "custom",
                "tokenizer": "standard",
                "filter": ["asciifolding", "lowercase", "haystack_ngram"],
            },
            "edgengram_analyzer": {
                "type": "custom",
                "tokenizer": "my_tokenizer",
                "filter": ["asciifolding", "lowercase"],
            },
        }
        tokenizer = {
            "standard": {"type": "standard"},
            "lowercase": {"type": "lowercase"},
            "my_tokenizer": {
                "type": "edge_ngram",
                "min_gram": 3,
                "max_gram": 15,
                "token_chars": ["letter", "digit"],
            },
        }
        filter = {
            "haystack_ngram": {
                "type": "ngram",
                "min_gram": 4,
                "max_gram": 5,
            },
            "haystack_edgengram": {
                "type": "edge_ngram",
                "min_gram": 2,
                "max_gram": 15,
            },
        }

        self.DEFAULT_SETTINGS["settings"]["analysis"]["tokenizer"] = tokenizer
        self.DEFAULT_SETTINGS["settings"]["analysis"]["analyzer"] = analyzer
        self.DEFAULT_SETTINGS["settings"]["analysis"]["filter"] = filter

    def build_schema(self, fields):
        content_field_name, mapping = super(AsciifoldingElasticBackend, self).build_schema(fields)

        for field_name, field_class in fields.items():
            field_mapping = mapping[field_class.index_fieldname]

            if field_mapping["type"] == "text" and field_class.indexed:
                if not hasattr(field_class, "facet_for"):
                    if field_class.field_type not in ("ngram", "edge_ngram"):
                        field_mapping["analyzer"] = "ascii_ngram_analyser"
                        field_mapping["fields"] = {
                            "exact": {
                                "type": "text",
                                "analyzer": "standard_analyzer",
                            },
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256,
                            },
                        }
                    else:
                        field_mapping["analyzer"] = "standard_analyzer"
                        field_mapping["fields"] = {
                            "ngram": {
                                "type": "text",
                                "analyzer": "ngram_analyzer",
                            },
                            "edgengram": {
                                "type": "text",
                                "analyzer": "edgengram_analyzer",
                            },
                            "exact": {
                                "type": "text",
                                "analyzer": "standard_analyzer",
                            },
                        }

            mapping.update({field_class.index_fieldname: field_mapping})
        return (content_field_name, mapping)


class AsciifoldingElasticSearchEngine(es_backend.Elasticsearch7SearchEngine):
    backend = AsciifoldingElasticBackend
