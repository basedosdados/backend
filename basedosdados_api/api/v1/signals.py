# -*- coding: utf-8 -*-
import logging

from django.db import models

from haystack.exceptions import NotHandled
from haystack.signals import BaseSignalProcessor

from basedosdados_api.api.v1.models import (
    Dataset,
    Organization,
    Table,
    RawDataSource,
    InformationRequest,
    Coverage,
)

logger = logging.getLogger("django")


class BDSignalProcessor(BaseSignalProcessor):
    """
    Allows for observing when saves/deletes fire & automatically updates the
    search engine appropriately.
    """

    def handle_save(self, sender, instance, **kwargs):
        """
        Given an individual model instance, determine which backends the
        update should be sent to & update the object on those backends.
        """
        using_backends = self.connection_router.for_write(instance=instance)

        for using in using_backends:
            try:
                index = self.connections[using].get_unified_index().get_index(Dataset)
                if sender == Dataset:
                    index.update_object(instance, using=using)
                elif sender == Organization:
                    ds = Dataset.objects.filter(organization__id=instance.id)
                    for instance in ds:
                        index.update_object(instance, using=using)
                elif sender == Coverage:
                    instance = (
                        Coverage.objects.filter(pk=instance.id).first().table.dataset
                    )
                    index.update_object(instance, using=using)
                elif sender in [Table, RawDataSource, InformationRequest]:
                    index.update_object(instance.dataset, using=using)
            except NotHandled:
                # Maybe log it or let the exception bubble?
                pass
            except Exception as e:
                logger.error(e)

    def setup(self):
        # Naive (listen to all model saves).
        models.signals.post_save.connect(self.handle_save)
        models.signals.post_delete.connect(self.handle_delete)
        # Efficient would be going through all backends & collecting all models
        # being used, then hooking up signals only for those.

    def teardown(self):
        # Naive (listen to all model saves).
        models.signals.post_save.disconnect(self.handle_save)
        models.signals.post_delete.disconnect(self.handle_delete)
        # Efficient would be going through all backends & collecting all models
        # being used, then disconnecting signals only for those.
