# -*- coding: utf-8 -*-
from django.db import models
from haystack.exceptions import NotHandled
from haystack.indexes import SearchIndex
from haystack.signals import BaseSignalProcessor
from loguru import logger

from backend.apps.api.v1.models import (
    Coverage,
    Dataset,
    DateTimeRange,
    InformationRequest,
    Organization,
    RawDataSource,
    Table,
)


class BDSignalProcessor(BaseSignalProcessor):
    """
    Allows for observing when saves/deletes fire
    and automatically updates the search engine appropriately
    """

    def handle_save(self, sender, instance, raw, **kwargs):
        """
        Given an individual model instance, determine which backends the
        update should be sent to and update the object on those backends.

        - If the instance is a fixture, ignore it
        - If the instance isn't a fixture, then update it
        """

        if raw:
            return None

        using_backends = self.connection_router.for_write(instance=instance)

        for using in using_backends:
            datasets: list[Dataset] = []
            try:
                if sender == Dataset:
                    datasets = [instance]
                elif sender == Organization:
                    datasets = instance.datasets.all()
                elif sender == Coverage:
                    resource = None
                    resource = resource or instance.table
                    resource = resource or instance.raw_data_source
                    resource = resource or instance.information_request
                    if resource and (dataset := resource.dataset):
                        datasets = [dataset]
                elif sender == DateTimeRange:
                    if coverage := instance.coverage:
                        resource = None
                        resource = resource or coverage.table
                        resource = resource or coverage.raw_data_source
                        resource = resource or coverage.information_request
                        if resource and (dataset := resource.dataset):
                            datasets = [dataset]
                elif sender in [Table, RawDataSource, InformationRequest]:
                    if dataset := instance.dataset:
                        datasets = [dataset]
                index: SearchIndex = (
                    self.connections[using]
                    .get_unified_index()
                    .get_index(Dataset)
                )  # fmt: skip
                for ds in datasets or []:
                    if ds.status and ds.status.slug in ["under_review", "excluded"]:
                        index.remove_object(ds, using=using)
                    else:
                        index.update_object(ds, using=using)
            except NotHandled as error:
                logger.warning(error)
            except Exception as error:
                logger.error(error)

    def setup(self):
        models.signals.post_save.connect(self.handle_save)
        models.signals.post_delete.connect(self.handle_delete)

    def teardown(self):
        models.signals.post_save.disconnect(self.handle_save)
        models.signals.post_delete.disconnect(self.handle_delete)
