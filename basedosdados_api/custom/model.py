# -*- coding: utf-8 -*-
from django.db import models


class BdmModel(models.Model):
    """
    An abstract base class model that provides whitelist of fields to be used
    for filtering in the GraphQL API.
    """

    class Meta:
        abstract = True
