# -*- coding: utf-8 -*-
# ruff: noqa

from uuid import UUID

import graphene
from django.utils import timezone
from graphene import Int, Mutation, String
from graphene_django import DjangoObjectType
from graphql_jwt.decorators import login_required

from backend.apps.account.models import Account
from backend.apps.api.v1.models import Table

from .models import TableUpdateSubscription


class TableUpdateSubscriptionType(DjangoObjectType):
    class Meta:
        model = TableUpdateSubscription
        fields = "__all__"


### Mutations


class CreateTableUpdateSubscription(Mutation):
    class Arguments:
        table_id = String()
        user_id = Int()

    table_update_subscription = graphene.Field(TableUpdateSubscriptionType)

    @login_required
    def mutate(self, info, table_id: str, user_id: int):
        # Verifica se já existe uma assinatura ativa para o usuário e a tabela
        try:
            table = Table.objects.get(id=UUID(table_id))
            user = Account.objects.get(id=user_id)

            existing_subscription = TableUpdateSubscription.objects.filter(
                user_id=user,
                table_id=table,
                status=True,  # Aqui você verifica apenas as assinaturas ativas
            ).first()

            if existing_subscription:
                # Se já existir, você pode retornar a assinatura existente ou lançar um erro
                raise Exception("Já existe uma assinatura ativa para esse usuário e tabela.")

            # Caso contrário, cria uma nova assinatura

            subscription = TableUpdateSubscription.objects.create(
                table=table,
                user=user,
                updated_at=table.last_updated_at,
                status=True,  # A assinatura será criada como ativa
            )

            return CreateTableUpdateSubscription(table_update_subscription=subscription)

        except Table.DoesNotExist:
            return Exception("Tabela não encontrada.")
        except Account.DoesNotExist:
            return Exception("Usuário não encontrado.")


class TableUpdateNotification:
    _table_upadate_notification = CreateTableUpdateSubscription.Field()


class DeactivateTableUpdateSubscription(Mutation):
    class Arguments:
        table_id = String()
        user_id = Int()

    table_update_subscription = graphene.Field(TableUpdateSubscriptionType)

    @login_required
    def mutate(self, info, table_id, user_id):
        # Verifica se já existe uma assinatura ativa para o usuário e a tabela
        try:
            table = Table.objects.get(id=UUID(table_id))
            user = Account.objects.get(id=user_id)

            subscription = TableUpdateSubscription.objects.filter(
                table=table,
                user=user,
                status=True,  # Apenas as assinaturas ativas
            ).first()

            if not subscription:
                # Se já existir, você pode retornar a assinatura existente ou lançar um erro
                raise Exception(
                    f"Não existe uma assinatura ativa para a tabela {table.name} e o usuário {user.username}."
                )

            # Atualizando o status para False e registrando a data de desativação
            subscription.status = False
            subscription.deactivate_at = timezone.now()  # Atualizando com a data e hora atual
            subscription.save()

            return CreateTableUpdateSubscription(table_update_subscription=subscription)

        except Table.DoesNotExist:
            return Exception("Tabela não encontrada.")
        except Account.DoesNotExist:
            return Exception("Usuário não encontrado.")


class DeactivateTableUpdateNotification:
    _deactivate_table_upadate_notification = DeactivateTableUpdateSubscription.Field()


class DeactivateAllTableUpdateSubscription(Mutation):
    class Arguments:
        user_id = Int()

    success = graphene.Boolean()
    deactivated_count = graphene.Int()

    @login_required
    def mutate(self, info, user_id):
        # Verifica se já existe uma assinatura ativa para o usuário e a tabela
        try:
            user = Account.objects.get(id=user_id)

            subscriptions_qs = TableUpdateSubscription.objects.filter(
                user=user,
                status=True,  # Apenas as assinaturas ativas
            ).all()

            if not subscriptions_qs:
                # Se já existir, você pode retornar a assinatura existente ou lançar um erro
                raise Exception(f"Não existe uma assinatura ativa para o usuário {user.username}.")

            deactivated_count = subscriptions_qs.update(status=False, deactivate_at=timezone.now())

            return DeactivateAllTableUpdateSubscription(
                success=True, deactivated_count=deactivated_count
            )

        except Account.DoesNotExist:
            return Exception("Usuário não encontrado.")


class DeactivateAllTableUpdateNotification:
    _deactivate_all_table_upadate_notification = DeactivateAllTableUpdateSubscription.Field()


### Querys


class StatusTableUpadateNotificationQueryType(DjangoObjectType):
    class Meta:
        model = TableUpdateSubscription
        fields = ("status",)


class StatusTableUpadateNotificationQuery(graphene.ObjectType):
    # Definindo a query para obter o status de uma inscrição
    status_table_update_notification = graphene.Field(
        StatusTableUpadateNotificationQueryType, table_id=String(), user_id=Int()
    )

    @login_required
    def resolve_status_table_update_notification(
        self, info, table_id: str, user_id: int
    ) -> TableUpdateSubscription | None:
        try:
            subscription = TableUpdateSubscription.objects.filter(
                table=table_id,
                user=user_id,
                status=True,
            ).exists()
            return TableUpdateSubscription(status=subscription)
        except TableUpdateSubscription.DoesNotExist:
            return None


class Query(StatusTableUpadateNotificationQuery, graphene.ObjectType):
    pass
