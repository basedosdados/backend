# -*- coding: utf-8 -*-
from __future__ import annotations

from urllib.parse import urlparse

from django.http import HttpResponseRedirect
from django.views import View

from bd_api.apps.api.v1.models import CloudTable, Dataset

URL_MAPPING = {
    "localhost:8080": "http://localhost:3000",
    "backend.basedosdados.org": "https://basedosdados.org",
    "staging.backend.basedosdados.org": "https://staging.basedosdados.org",
    "development.backend.basedosdados.org": "https://development.basedosdados.org",
}


class DatasetRedirectView(View):
    """View to redirect old dataset urls"""

    def get(self, request, *args, **kwargs):
        """Redirect to new dataset url"""
        url = request.build_absolute_uri()
        domain = URL_MAPPING[urlparse(url).netloc]

        if dataset := request.GET.get("dataset"):
            dataset_slug = dataset.replace("-", "_")

            if resource := CloudTable.objects.filter(
                gcp_dataset_id=dataset_slug
            ).first():
                return HttpResponseRedirect(
                    f"{domain}/dataset/{resource.table.dataset.id}"
                )

            if resource := Dataset.objects.filter(slug__icontains=dataset_slug).first():
                return HttpResponseRedirect(f"{domain}/dataset/{resource.id}")

        return HttpResponseRedirect(f"{domain}/404")
