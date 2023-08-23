# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.views.generic import TemplateView


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
