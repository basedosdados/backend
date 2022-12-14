# -*- coding: utf-8 -*-
from rest_framework import routers

from basedosdados_api.custom.routers import IndexRouter
from basedosdados_api.api.v1 import views

private_router = routers.DefaultRouter()
private_router.register(
    r"organizations", views.OrganizationViewSet, basename="organization-private"
)
private_router.register(r"datasets", views.DatasetViewSet, basename="dataset-private")
private_router.register(r"tables", views.TableViewSet, basename="table-private")
private_router.register(r"columns", views.ColumnViewSet, basename="column-private")
private_router.register(
    r"cloudtables", views.CloudTableViewSet, basename="cloudtable-private"
)

public_router = routers.DefaultRouter()
public_router.register(
    r"organizations", views.OrganizationReadOnlyViewSet, basename="organization-public"
)
public_router.register(
    r"datasets", views.DatasetReadOnlyViewSet, basename="dataset-public"
)
public_router.register(r"tables", views.TableReadOnlyViewSet, basename="table-public")
public_router.register(
    r"columns", views.ColumnReadOnlyViewSet, basename="column-public"
)
public_router.register(
    r"cloudtables", views.CloudTableReadOnlyViewSet, basename="cloudtable-public"
)

router = IndexRouter(
    routers={"private": private_router, "public": public_router},
    name="V1",
    swagger_operation_summary="Versão 1 da API do Base dos Dados",
)

urlpatterns = router.to_urlpatterns()
