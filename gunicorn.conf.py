# -*- coding: utf-8 -*-
import os


def post_fork(server, worker):
    import googlecloudprofiler

    api_name = os.environ.get("API_NAME", "api-unknown")
    googlecloudprofiler.start(
        service=f"{api_name}-gunicorn",
        service_version="1.0.0",
        verbose=1,
        # Mesmo problema encontrado no Huey (ver run_huey.py): o Wall
        # profiler usa SIGALRM num handler que só roda de forma confiável
        # na thread principal. Com --threads 4, os workers do Gunicorn têm
        # o mesmo perfil de múltiplas threads disputando o GIL, gerando
        # BlockingIOError no wakeup fd em alta frequência (~1000/min,
        # engolindo o buffer de log inteiro do pod). CPU profiling não tem
        # essa limitação, então mantemos só ele.
        disable_wall_profiling=True,
    )
