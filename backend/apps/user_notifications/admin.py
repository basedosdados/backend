# -*- coding: utf-8 -*-
# Register your models here.
from django.contrib import admin

from .models import TableUpdateSubscription


class TableUpdateSubscriptionAdmin(admin.ModelAdmin):
    # Campos que serão exibidos na lista de objetos
    list_display = (
        "id",
        "table",
        "user",
        "created_at",
        "deactivate_at",
        "last_notification",
        "updated_at",
        "status",
    )

    # Filtros laterais para facilitar a busca
    list_filter = ("status", "table", "user")

    # Campos que podem ser pesquisados diretamente
    search_fields = ("table__name", "user__username")

    # Campos que serão editáveis diretamente na lista (inline)
    list_editable = ("status",)

    # Exibir um campo de data mais legível na interface
    date_hierarchy = "created_at"

    # Definindo o formulário de exibição de detalhes
    fieldsets = (
        (None, {"fields": ("table", "user", "status")}),
        (
            "Datas",
            {
                "fields": ("created_at", "deactivate_at", "last_notification", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    # Campos que não serão mostrados no formulário de edição
    readonly_fields = ("created_at", "deactivate_at")

    # Exibir os campos na ordem desejada no formulário de edição
    ordering = ("-created_at",)


# Registrar o modelo e a classe de admin personalizada
admin.site.register(TableUpdateSubscription, TableUpdateSubscriptionAdmin)
