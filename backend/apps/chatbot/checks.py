# -*- coding: utf-8 -*-
import os

from django.core.checks import Info, Warning, register


@register()
def check_gcloud_env_vars(app_configs, **kwargs):
    """Validate chatbot environment variables."""
    checks = []

    sa_file = os.getenv("CHATBOT_CREDENTIALS")
    if not sa_file:
        checks.append(
            Warning(
                "CHATBOT_CREDENTIALS not set - chatbot will not work properly",
                hint="Set CHATBOT_CREDENTIALS=/path/to/service-account.json\n",
                id="chatbot.W001",
            )
        )
    elif not os.path.exists(sa_file):
        checks.append(
            Warning(
                f"Service account file {sa_file} not found - chatbot will not work properly",
                hint="Ensure the file exists at the specified path\n",
                id="chatbot.W002",
            )
        )

    if not os.getenv("BIGQUERY_PROJECT_ID"):
        checks.append(
            Warning(
                "BIGQUERY_PROJECT_ID not set - chatbot will not work properly",
                hint="Set BIGQUERY_PROJECT_ID=your-gcp-project-id\n",
                id="chatbot.W003",
            )
        )

    if not os.getenv("LANGSMITH_TRACING"):
        checks.append(
            Warning(
                "LANGSMITH_TRACING not set - tracing will be disabled",
                hint="Set LANGSMITH_TRACING=true\n",
                id="chatbot.W004",
            )
        )

    if not os.getenv("LANGSMITH_API_KEY"):
        checks.append(
            Warning(
                "LANGSMITH_API_KEY not set - tracing will be disabled",
                hint="Set LANGSMITH_API_KEY=your-langsmith-api-key\n",
                id="chatbot.W005",
            )
        )

    if not os.getenv("LANGSMITH_PROJECT"):
        checks.append(
            Warning(
                "LANGSMITH_PROJECT not set - project 'default' will be used",
                hint="Set LANGSMITH_PROJECT=your-project-name",
                id="chatbot.W006",
            )
        )

    if not os.getenv("BACKEND_BASE_URL"):
        checks.append(
            Info(
                "BACKEND_BASE_URL not set - defaulting to http://localhost:8000",
                hint=(
                    "Default http://localhost:8000 works for same-server deployments. "
                    "Override only if you need an external backend, e.g., https://backend.basedosdados.org\n"
                ),
                id="chatbot.I001",
            )
        )

    return checks
