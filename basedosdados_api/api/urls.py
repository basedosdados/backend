# -*- coding: utf-8 -*-
from django.urls import include, path
from basedosdados_api.custom.routers import IndexRouter
from basedosdados_api.api.v1.urls import urlpatterns as v1_urlpatterns

urlpatterns = [
    path("v1/", include(v1_urlpatterns)),
]

router = IndexRouter(
    urlpatterns=urlpatterns,
    name="API Root",
    swagger_operation_summary="Acessa a API do Base dos Dados",
)

urlpatterns = router.to_urlpatterns()
