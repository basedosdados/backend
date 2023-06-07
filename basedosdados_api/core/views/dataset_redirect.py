# -*- coding: utf-8 -*-
from urllib.parse import urlparse

from django.http import HttpResponseRedirect
from django.views import View

from basedosdados_api.api.v1.models import Dataset, CloudTable


class DatasetRedirectView(View):
    """View to redirect old dataset urls."""

    def get(self, request, *args, **kwargs):
        """Redirect to new dataset url."""
        full_url = request.build_absolute_uri()  # noqa
        domain = urlparse(full_url).netloc

        dataset = request.GET.get("dataset")
        dataset_slug = dataset.replace("-", "_")

        try:
            redirect_url = CloudTable.objects.filter(
                gcp_dataset_id=dataset_slug
            ).first()
            if not redirect_url:
                raise CloudTable.DoesNotExist
            redirect_url = (
                f"http://{domain}/dataset/{str(redirect_url.table.dataset.id)}"
            )
        except CloudTable.DoesNotExist:
            # não tem cloud table, procura pelo nome do dataset
            try:
                new_ds = Dataset.objects.filter(slug__icontains=dataset_slug).first()
                redirect_url = f"http://{domain}/dataset/{str(new_ds.id)}"
            except Dataset.DoesNotExist:
                redirect_url = f"http://{domain}/404"

        return HttpResponseRedirect(redirect_url)
