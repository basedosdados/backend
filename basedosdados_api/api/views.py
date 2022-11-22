# -*- coding: utf-8 -*-
from rest_framework import viewsets

from basedosdados_api.api.models import Category
from basedosdados_api.api.serializers import CategorySerializer


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer

    def get_queryset(self):
        queryset = Category.objects.all().order_by("name")
        name = self.request.query_params.get("name", None)
        if name is not None:
            queryset = queryset.filter(name=name)
        return queryset
