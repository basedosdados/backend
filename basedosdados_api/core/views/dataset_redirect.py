# -*- coding: utf-8 -*-
from urllib.parse import urlparse

from django.http import HttpResponseRedirect
from django.views import View

from basedosdados_api.api.v1.models import CloudTable, Dataset

URL_MAPPING = {
    "localhost:8001": "localhost:3000",
    "api.basedosdados.org": "basedosdados.org",
    "staging.api.basedosdados.org": "staging.basedosdados.org",
    "development.api.basedosdados.org": "development.basedosdados.org",
}


class DatasetRedirectView(View):
    """View to redirect old dataset urls."""

    def get(self, request, *args, **kwargs):
        """Redirect to new dataset url."""
        full_url = request.build_absolute_uri()
        domain = urlparse(full_url).netloc

        dataset = request.GET.get("dataset")
        dataset_slug = dataset.replace("-", "_")
        redirect_domain = URL_MAPPING[domain]

        try:
            redirect_url = CloudTable.objects.filter(gcp_dataset_id=dataset_slug).first()
            if not redirect_url:
                raise CloudTable.DoesNotExist
            redirect_url = f"http://{redirect_domain}/dataset/{str(redirect_url.table.dataset.id)}"
        except CloudTable.DoesNotExist:
            try:
                new_ds = Dataset.objects.filter(slug__icontains=dataset_slug).first()
                redirect_url = f"http://{redirect_domain}/dataset/{str(new_ds.id)}"
            except Dataset.DoesNotExist:
                redirect_url = f"http://{redirect_domain}/404"

        return HttpResponseRedirect(redirect_url)
