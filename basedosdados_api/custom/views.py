# -*- coding: utf-8 -*-
from collections import OrderedDict
from typing import Callable, List, Union

from django.urls import URLPattern, URLResolver
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView


class IndexView(APIView):
    deprecated_func: Callable[[], bool] = None
    ignore_admin: bool = None
    router_names: List[str] = None
    swagger_operation_description: str = (None,)
    swagger_operation_summary: str = (None,)
    urlpatterns: List[Union[URLPattern, URLResolver]] = None
    view_name: str = None

    def __init__(
        self,
        *,
        deprecated_func: Callable[[], bool] = lambda: False,
        ignore_admin: bool = True,
        router_names: List[str] = None,
        swagger_operation_description: str = None,
        swagger_operation_summary: str = None,
        urlpatterns: List[Union[URLPattern, URLResolver]] = None,
        view_name: str = "Index",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.deprecated_func = deprecated_func
        self.ignore_admin = ignore_admin
        self.router_names = router_names or []
        self.swagger_operation_description = swagger_operation_description
        self.swagger_operation_summary = swagger_operation_summary
        self.urlpatterns = urlpatterns or []
        self.view_name = view_name

        @swagger_auto_schema(
            deprecated=self.deprecated_func(),
            operation_summary=self.swagger_operation_summary,
            operation_description=self.swagger_operation_description,
        )
        def get(request, format=None):
            current_url = request.build_absolute_uri().rstrip("/")
            data = OrderedDict()
            for router_name in self.router_names:
                data[router_name] = f"{current_url}/{router_name}/"
            for urlpatterns in self.urlpatterns:
                if isinstance(urlpatterns, URLResolver):
                    pattern = str(urlpatterns.pattern).rstrip("/")
                    if self.ignore_admin and pattern == "admin":
                        continue
                    data[
                        str(urlpatterns.pattern).rstrip("/")
                    ] = f"{current_url}/{str(urlpatterns.pattern)}"
                elif isinstance(urlpatterns, URLPattern):
                    # Parse the URLPattern to something readable
                    base_pattern = str(urlpatterns.pattern).rstrip("$")
                    base_pattern = base_pattern.rstrip("/")
                    base_pattern = base_pattern.replace("^", "")
                    base_pattern = base_pattern.replace("<", "{")
                    base_pattern = base_pattern.replace(">", "}")
                    # If base_pattern is empty, skip it
                    if not base_pattern:
                        continue
                    # If we want to skip admin, skip it
                    if self.ignore_admin and base_pattern == "admin":
                        continue
                    # If we have a regex group, skip it
                    if "(" in base_pattern or ")" in base_pattern:
                        continue
                    data[base_pattern] = f"{current_url}/{base_pattern}/"
            return Response(data)

        self.get = get

    def get_view_name(self):
        return self.view_name
