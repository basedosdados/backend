from haystack import indexes
from .models import (
    Dataset,
)


class DatasetIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=False)
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

    # id = indexes.CharField(model_attr='id')
    # name = indexes.CharField(model_attr='name')
    # description = indexes.CharField(model_attr='description')
    # covered_by_dictionary = indexes.CharField(model_attr='covered_by_dictionary')
    # measurement_unit = indexes.CharField(model_attr='measurement_unit')
    # contains_sensitive_data = indexes.CharField(model_attr='contains_sensitive_data')
    # observations = indexes.CharField(model_attr='observations')
    # is_in_staging = indexes.CharField(model_attr='is_in_staging')
    # is_partition = indexes.CharField(model_attr='is_partition')

    # def prepare_text(self, obj):
    #     return f"{obj.name} {obj.description}"

    # def get_model(self):
    #     return Column

    # def index_queryset(self, using=None):
    #     return self.get_model().objects.all()