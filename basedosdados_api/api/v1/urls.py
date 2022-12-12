# -*- coding: utf-8 -*-
from rest_framework import routers

from basedosdados_api.api.v1 import views

router = routers.DefaultRouter()
router.register(r"organizations", views.OrganizationViewSet, basename="organization")
router.register(r"datasets", views.DatasetViewSet, basename="dataset")
router.register(r"tables", views.TableViewSet, basename="table")
router.register(r"columns", views.ColumnViewSet, basename="column")
router.register(r"cloudtables", views.CloudTableViewSet, basename="cloudtable")
