# -*- coding: utf-8 -*-
import os

from huey.contrib.djhuey.management.commands.run_huey import (
    Command as HueyCommand,
)


class Command(HueyCommand):
    """Inicia o Cloud Profiler antes de rodar o consumer do Huey.

    Sobrescreve o comando `run_huey` da própria lib (Django usa o último
    app em INSTALLED_APPS que define o mesmo nome de comando).
    """

    def handle(self, *args, **options):
        import googlecloudprofiler

        api_name = os.environ.get("API_NAME", "api-unknown")
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
