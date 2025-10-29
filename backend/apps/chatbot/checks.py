# -*- coding: utf-8 -*-
import os

from django.core.checks import Warning, register


@register()
def check_gcloud_env_vars(app_configs, **kwargs):
    """Validate Google Cloud environment variables (warnings only)."""
    warnings = []

    sa_file = os.getenv("CHATBOT_CREDENTIALS")
    if not sa_file:
        warnings.append(
            Warning(
                "CHATBOT_CREDENTIALS not set - chatbot will be disabled",
                hint="Set CHATBOT_CREDENTIALS=/path/to/service-account.json\n",
                id="chatbot.W001",
            )
        )
    elif not os.path.exists(sa_file):
        warnings.append(
            Warning(
                f"Service account file {sa_file} not found - chatbot will be disabled",
                hint="Ensure the file exists at the specified path\n",
                id="chatbot.W002",
            )
        )

    if not os.getenv("QUERY_PROJECT_ID"):
        warnings.append(
            Warning(
                "QUERY_PROJECT_ID not set - chatbot will be disabled",
                hint="Set QUERY_PROJECT_ID=your-gcp-project-id\n",
                id="chatbot.W003",
            )
        )

    if not os.getenv("MODEL_URI"):
        warnings.append(
            Warning(
                "MODEL_URI not set - chatbot will be disabled",
                hint="Set a valid model uri like 'google_vertexai:gemini-2.5-flash'\n",
                id="chatbot.W004",
            )
        )

    if not os.getenv("LANGCHAIN_TRACING_V2"):
        warnings.append(
            Warning(
                "LANGCHAIN_TRACING_V2 not set - tracing will be disabled",
                hint="Set LANGCHAIN_TRACING_V2=true\n",
                id="chatbot.W005",
            )
        )

    if not os.getenv("LANGCHAIN_API_KEY"):
        warnings.append(
            Warning(
                "LANGCHAIN_API_KEY not set - tracing will be disabled",
                hint="Set LANGCHAIN_API_KEY=your-langsmith-api-key\n",
                id="chatbot.W006",
            )
        )

    return warnings
