from haystack import indexes
from .models import Dataset

class DatasetIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=False)
    name = indexes.CharField(model_attr='name')
    description = indexes.CharField(model_attr='description')
    id = indexes.CharField(model_attr='id')
    organization = indexes.CharField(model_attr='organization')
    created_at = indexes.DateTimeField(model_attr='created_at')
    updated_at = indexes.DateTimeField(model_attr='updated_at')

    def prepare_text(self, obj):
        return f"{obj.name} {obj.description}"

    def get_model(self):
        return Dataset

    def index_queryset(self, using=None):
        return self.get_model().objects.all()
