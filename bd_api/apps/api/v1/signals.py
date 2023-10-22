# -*- coding: utf-8 -*-
from django.db import models
from haystack.exceptions import NotHandled
from haystack.signals import BaseSignalProcessor
from loguru import logger

from bd_api.apps.api.v1.models import (
    Coverage,
    Dataset,
    InformationRequest,
    Organization,
    RawDataSource,
    Table,
)


class BDSignalProcessor(BaseSignalProcessor):
    """
    Allows for observing when saves/deletes fire & automatically updates the
    search engine appropriately.
    """

    def handle_save(self, sender, instance, raw, **kwargs):
        """
        Given an individual model instance, determine which backends the
        update should be sent to & update the object on those backends.

        - If the instance is a fixture, ignore it
        - If the instance isn't a fixture, then update it
        """

        if raw:
            return None

        using_backends = self.connection_router.for_write(instance=instance)

        for using in using_backends:
            datasets = []
            try:
                index = self.connections[using].get_unified_index().get_index(Dataset)
                if sender == Dataset:
                    datasets = [instance]
                elif sender == Organization:
                    datasets = Dataset.objects.filter(organization__id=instance.id)
                elif sender == Coverage:
                    if coverage := Coverage.objects.filter(pk=instance.id).first():
                        if table := coverage.table:
                            if dataset := table.dataset:
                                datasets = [dataset]
                elif sender in [Table, RawDataSource, InformationRequest]:
                    if dataset := instance.dataset:
                        datasets = [dataset]
                for ds in datasets or []:
                    index.update_object(ds, using=using)
            except NotHandled as error:
                logger.warning(error)
            except Exception as error:
                logger.error(error)

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
