# -*- coding: utf-8 -*-
from rest_framework import serializers

from basedosdados_api.api.v1.models import Category


class CategorySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"
