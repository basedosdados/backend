# -*- coding: utf-8 -*-
from rest_framework import routers

from basedosdados_api.api.v1 import views

router = routers.DefaultRouter()
router.register(r"categories", views.CategoryViewSet, basename="category")
