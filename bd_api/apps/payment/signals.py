# -*- coding: utf-8 -*-
from django.db.models.signals import post_save
from django.dispatch import receiver
from djstripe.models import Customer as DJStripeCustomer

from bd_api.apps.account.models import Account
from bd_api.utils import is_prod


@receiver(post_save, sender=Account)
def create_stripe_customer(sender, instance, created, **kwargs):
    """Create stripe customer from after registration"""

    if created and is_prod():
        DJStripeCustomer.create(subscriber=instance)
