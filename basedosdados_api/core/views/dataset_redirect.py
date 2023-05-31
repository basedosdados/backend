# -*- coding: utf-8 -*-
from django.http import HttpResponseRedirect

from django.views import View

from basedosdados_api.api.v1.models import Dataset


class DatasetRedirectView(View):
    """View to redirect old dataset urls."""

    def get(self, request, *args, **kwargs):
        """Redirect to new dataset url."""
        dataset_slug = request.GET.get("dataset")
        dataset_slug_list = dataset_slug.split("-")
        # O padrão mais recente é <local>_<org>_<dataset>
        # é preciso verificar os outros padrões antes de redirecionar
        # para o 404
        try:
            slug = dataset_slug_list[2]
            dataset_id = Dataset.objects.get(slug=slug).pk
            redirect_url = f"http://basedosdados.org/dataset/{dataset_id}/"
        except Dataset.DoesNotExist:
            redirect_url = "http://basedosdados.org/404/"
        except IndexError:
            redirect_url = "http://basedosdados.org/404/"

        return HttpResponseRedirect(redirect_url)
