# -*- coding: utf-8 -*-
from basedosdados_api.custom.routers import IndexRouter
from basedosdados_api.api.v1.urls import router as v1_router

router = IndexRouter(
    routers={"v1": v1_router},
    name="V1",
    swagger_operation_summary="Acessa a API do Base dos Dados",
)

urlpatterns = router.to_urlpatterns()
