# -*- coding: utf-8 -*-
"""Inicialização do Cloud Profiler, desligado por padrão."""

import os

import googlecloudprofiler


def start_profiler(service_name: str) -> None:
    """Inicia o Cloud Profiler se `CLOUD_PROFILER_ENABLED=true`.

    Args:
        service_name: nome do serviço no Cloud Profiler.
    """
    if os.environ.get("CLOUD_PROFILER_ENABLED", "false").lower() != "true":
        return

    googlecloudprofiler.start(
        service=service_name,
        service_version="1.0.0",
        verbose=1,
        # O profiling de Wall time usa SIGALRM e só roda no handler da
        # thread principal, que fica majoritariamente bloqueada em I/O
        # e disputando o GIL com as outras threads. Nesse ambiente o
        # sinal nunca é processado a tempo, gerando só erro
        # (BlockingIOError no wakeup fd) e zero profiles. CPU profiling
        # não tem essa limitação, então mantemos só ele.
        disable_wall_profiling=True,
    )
