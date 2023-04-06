from haystack import indexes
from .models import (
    Dataset,
)


class DatasetIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    slug = indexes.CharField(model_attr='slug')
    name = indexes.CharField(model_attr='name')
    description = indexes.CharField(model_attr='description', null=True)
    organization = indexes.CharField(model_attr='organization__name')
    themes = indexes.MultiValueField(model_attr='themes__name', null=True)
    tags = indexes.MultiValueField(model_attr='tags__name', null=True)
    created_at = indexes.DateTimeField(model_attr='created_at')
    updated_at = indexes.DateTimeField(model_attr='updated_at')

    def get_model(self):
        return Dataset

    def index_queryset(self, using=None):
        return self.get_model().objects.all()
