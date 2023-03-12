from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render
from django.views import View
from django.views.generic import TemplateView

from basedosdados_api.api.v1.models import Organization
from basedosdados_api.core.forms import DatasetForm


class HomeView(TemplateView):
    """Home view."""

    def get(self, request, *args, **kwargs):
        """Render home page."""
        context = {
            "nome_pagina": "Home",
        }
        if self.request.user.is_authenticated:
            context.update(
                {
                    "name": request.user.get_full_name(),
                    "organizations": request.user.get_organization(),
                }
            )

        return render(request, "core/home.html", context=context)


class DatasetView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Dataset view."""
    login_url = "/accounts/login/"
    redirect_field_name = "redirect_to"
    template_name = "core/dataset.html"
    form_class = DatasetForm

    def test_func(self):
        """
        Check if user is part of the organization that owns the dataset
        and if has the correct permissions.
        """
        dataset_id = self.request.resolver_match.kwargs.get("id")
        # TODO: check if user has permission to access dataset based on roles and permissions
        organization = Organization.objects.get(datasets__id=dataset_id)
        orgs = [org for org in self.request.user.organizations.all()]

        return organization in orgs

    def get(self, request, *args, **kwargs):
        """Render dataset page."""
        context = {
            "nome_pagina": "Dataset",
            "name": request.user.get_full_name(),
            "form": self.form_class,
        }
        return render(request, self.template_name, context=context)
