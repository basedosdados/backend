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
        )
        super().handle(*args, **options)
