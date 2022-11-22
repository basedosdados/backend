# -*- coding: utf-8 -*-
from typing import Any, Callable, Dict, List

from django.urls import include, path
from rest_framework.routers import BaseRouter

from basedosdados_api.custom.views import IndexView


class IndexRouter:
    def __init__(
        self,
        routers: Dict[str, BaseRouter] = None,
        urlpatterns: List[Any] = None,
        name: str = "Index",
        deprecated_func: Callable[[], bool] = lambda: False,
        swagger_operation_description: str = None,
        swagger_operation_summary: str = None,
    ):
        self.routers = routers or {}
        self.urlpatterns = urlpatterns or []
        self.name = name
        self.deprecated_func = deprecated_func
        self.swagger_operation_description = swagger_operation_description
        self.swagger_operation_summary = swagger_operation_summary
        self._index = IndexView(
            router_names=list(self.routers.keys()),
            urlpatterns=self.urlpatterns,
            view_name=self.name,
            deprecated_func=self.deprecated_func,
            swagger_operation_description=self.swagger_operation_description,
            swagger_operation_summary=self.swagger_operation_summary,
        )

    def to_urlpatterns(self):
        urlpatterns = self.urlpatterns
        urlpatterns.append(
            path(
                "",
                self._index.as_view(
                    router_names=list(self.routers.keys()),
                    urlpatterns=self.urlpatterns,
                    view_name=self.name,
                    deprecated_func=self.deprecated_func,
                    swagger_operation_description=self.swagger_operation_description,
                    swagger_operation_summary=self.swagger_operation_summary,
                ),
                name="index",
            )
        )
        for name, router in self.routers.items():
            urlpatterns.append(path(name + "/", include(router.urls)))
        return urlpatterns
