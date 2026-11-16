# -*- coding: utf-8 -*-
import os

from backend.custom.profiling import start_profiler
from backend.custom.tracing import init_tracing


def post_fork(server, worker):
    api_name = os.environ.get("API_NAME", "api-unknown")
    init_tracing(f"{api_name}-gunicorn")
    start_profiler(f"{api_name}-gunicorn")
