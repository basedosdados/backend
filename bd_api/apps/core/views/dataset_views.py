# -*- coding: utf-8 -*-
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from bd_api.apps.account.models import BDRole
from bd_api.apps.api.v1.models import Dataset, Organization


class DatasetCreateView(
    LoginRequiredMixin,
    CreateView,
):
    """Dataset view."""

    model = Dataset
    # template_name = "core/dataset.html"
    fields = ["name", "description", "organization"]

    def form_valid(self, form):
        """Add user to form."""
        form.instance.owner = self.request.user
        return super().form_valid(form)


class DatasetUpdateView(
    UserPassesTestMixin,
    LoginRequiredMixin,
    UpdateView,
):
    """Dataset view."""

    model = Dataset
    template_name = "core/dataset_form.html"
    fields = [
        "name",
        "description",
        "organization",
        "themes",
        "tags",
        "slug",
        "name_pt",
        "description_pt",
        "name_en",
        "description_en",
        "name_es",
        "description_es",
    ]

    def test_func(self):
        """
        Check if user is part of the organization that owns the dataset
        and if has the correct permissions.
        """
        if self.request.user.is_staff:
            return True
        dataset_id = self.request.resolver_match.kwargs.get("pk")
        organization = Organization.objects.get(datasets__id=dataset_id)
        # orgs = [org for org in self.request.user.organizations.all()]
        perms = []
        try:
            for group in self.request.user.groups.all():
                role = group.roles.get(bdgrouprole__organization__slug=organization)
                if role:
                    perms += [r.codename for r in role.permissions.all()]
        except BDRole.DoesNotExist:
            pass

        return "view_dataset" in perms

    def get_success_url(self):
        return reverse("dataset-detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["name"] = self.request.user.get_full_name()
        context["dataset"] = self.object
        return context


class DatasetDeleteView(
    UserPassesTestMixin,
    LoginRequiredMixin,
    DeleteView,
):
    """Dataset view."""

    model = Dataset
    # template_name = "core/dataset.html"
    fields = ["name", "description", "organization"]
    success_url = "/"

    def test_func(self):
        """
        Check if user is part of the organization that owns the dataset
        and if has the correct permissions.
        """
        if self.request.user.is_staff:
            return True
        dataset_id = self.request.resolver_match.kwargs.get("id")

        organization = Organization.objects.get(datasets__id=dataset_id)
        # orgs = [org for org in self.request.user.organizations.all()]
        perms = []
        try:
            for group in self.request.user.groups.all():
                role = group.roles.get(bdgrouprole__organization__slug=organization)
                if role:
                    perms += [r.codename for r in role.permissions.all()]
        except BDRole.DoesNotExist:
            pass

        return "view_dataset" in perms
