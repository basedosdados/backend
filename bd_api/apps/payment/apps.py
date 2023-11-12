# -*- coding: utf-8 -*-
from djstripe.apps import DjstripeAppConfig


class PaymentsConfig(DjstripeAppConfig):
    verbose_name = "Stripe"

    def ready(self):
        super().ready()
        import bd_api.apps.payment.signals  # noqa
        import bd_api.apps.payment.webhooks  # noqa
