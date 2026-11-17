# -*- coding: utf-8 -*-
import os

from huey.contrib.djhuey import HUEY
from huey.contrib.djhuey.management.commands.run_huey import (
    Command as HueyCommand,
)

from backend.custom.profiling import start_profiler
from backend.custom.tracing import init_tracing, instrument_huey


class Command(HueyCommand):
    """Inicia o Cloud Profiler e o tracing antes de rodar o consumer do Huey."""

    def handle(self, *args, **options):
        api_name = os.environ.get("API_NAME", "api-unknown")
        init_tracing(f"{api_name}-huey")
        instrument_huey(HUEY)
        start_profiler(f"{api_name}-huey")
        super().handle(*args, **options)
