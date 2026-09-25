# -*- coding: utf-8 -*-
"""Settings used by the test suite.

Inherits the local settings and neutralises the external services the suite has
no business talking to. Without this every ``save()`` in a test tries to reach
Elasticsearch, fails, and logs a traceback.
"""

from os import getenv

from .local import *  # noqa: F401,F403

# Search: no Elasticsearch in CI. Use the in-memory backend and drop the signal
# processor so model saves don't attempt to index.
HAYSTACK_CONNECTIONS = {
    "default": {
        "ENGINE": "haystack.backends.simple_backend.SimpleEngine",
    }
}
HAYSTACK_SIGNAL_PROCESSOR = "haystack.signals.BaseSignalProcessor"

# Email: keep messages in memory instead of opening SMTP connections.
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# JWT: base settings read this from the environment and fall back to None, which
# makes django-graphql-jwt sign with alg="none" and reject every login.
GRAPHQL_JWT = {  # noqa: F405
    **GRAPHQL_JWT,  # noqa: F405
    "JWT_ALGORITHM": getenv("DJANGO_JWT_ALGORITHM", "HS256"),
}

# Note: do not swap in a faster password hasher here. Account.save() validates the
# stored hash with is_valid_encoded_password(), which assumes a four-part
# "algorithm$iterations$salt$hash" encoding. A three-part hasher such as MD5 fails
# that check and the model silently re-hashes an already-hashed password.
