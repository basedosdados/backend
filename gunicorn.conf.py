# -*- coding: utf-8 -*-
import os


def post_fork(server, worker):
    import googlecloudprofiler

    api_name = os.environ.get("API_NAME", "api-unknown")
    googlecloudprofiler.start(
        service=f"{api_name}-gunicorn",
        service_version="1.0.0",
        verbose=1,
    )
