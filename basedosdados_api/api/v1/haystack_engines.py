"""
Based on the following docs:
https://gregbrown.co/code/haystack-character-folding/
https://github.com/mounirmesselmeni/MounirMesselmeni.github.io/tree/master/2015/12/13/enable-asciifolding-in-elasticsearchhaystack
They are outdated, as are docs from 2015
"""

from abc import ABCMeta

from haystack import indexes
from haystack.backends import elasticsearch7_backend as es_backend


class AsciifoldingElasticBackend(es_backend.Elasticsearch7SearchBackend, metaclass=ABCMeta):

    def __init__(self, *args, **kwargs):
        super(AsciifoldingElasticBackend, self).__init__(*args, **kwargs)
        analyzer = {
            "ascii_analyser": {
                "tokenizer": "standard",
                "filter": ["asciifolding", "lowercase"]
            },
            "ngram_analyzer": {
                "type": "custom",
                "tokenizer": "lowercase",
                "filter": ["haystack_ngram", "asciifolding"]
            },
            "edgengram_analyzer": {
                "type": "custom",
                "tokenizer": "lowercase",
                "filter": ["haystack_edgengram", "asciifolding"]
            }
        }
        self.DEFAULT_SETTINGS['settings']['analysis']['analyzer'] = analyzer

    def build_schema(self, fields):
        content_field_name, mapping = super(AsciifoldingElasticBackend,
                                            self).build_schema(fields)

        for field_name, field_class in fields.items():
            field_mapping = mapping[field_class.index_fieldname]

            if field_mapping['type'] == 'text' and field_class.indexed:
                if not hasattr(field_class, 'facet_for') and not field_class.field_type in ('ngram', 'edge_ngram'):
                    field_mapping['analyzer'] = "ascii_analyser"
            print(field_mapping)
            print(field_class.indexed)
            print(field_class.__dict__)

            mapping.update({field_class.index_fieldname: field_mapping})
        return (content_field_name, mapping)


class AsciifoldingElasticSearchEngine(es_backend.Elasticsearch7SearchEngine):
    backend = AsciifoldingElasticBackend
