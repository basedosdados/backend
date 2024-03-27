# -*- coding: utf-8 -*-
from djstripe.apps import DjstripeAppConfig


class PaymentConfig(DjstripeAppConfig):
    verbose_name = "Pagamentos"

    def ready(self):
        super().ready()
        import bd_api.apps.account_payment.signals  # noqa
        import bd_api.apps.account_payment.webhooks  # noqa
