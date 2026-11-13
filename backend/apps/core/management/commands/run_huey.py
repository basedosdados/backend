# -*- coding: utf-8 -*-
import os

import googlecloudprofiler
from huey.contrib.djhuey import HUEY
from huey.contrib.djhuey.management.commands.run_huey import (
    Command as HueyCommand,
)

from backend.custom.tracing import init_tracing, instrument_huey


class Command(HueyCommand):
    """Inicia o Cloud Profiler e o tracing antes de rodar o consumer do Huey."""

    def handle(self, *args, **options):
        api_name = os.environ.get("API_NAME", "api-unknown")
        init_tracing(f"{api_name}-huey")
        instrument_huey(HUEY)
        googlecloudprofiler.start(
            service=f"{api_name}-huey",
            service_version="1.0.0",
            verbose=1,
            # O profiling de Wall time usa SIGALRM e só roda no handler da
            # thread principal, que fica majoritariamente bloqueada em I/O
            # do Redis e disputando o GIL com as outras threads do Huey
            # (scheduler, health-check, workers). Nesse ambiente o sinal
            # nunca é processado a tempo, gerando só erro
            # (BlockingIOError no wakeup fd) e zero profiles. CPU profiling
            # não tem essa limitação, então mantemos só ele.
            disable_wall_profiling=True,
        )
        super().handle(*args, **options)
