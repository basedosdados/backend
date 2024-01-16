# -*- coding: utf-8 -*-
from graphene import ID, Boolean, Mutation

from bd_api.apps.account.models import Account


class DeleteAccountPictureMutation(Mutation):
    """Delete picture of account"""

    ok = Boolean()

    class Arguments:
        id = ID(required=True, description="Account ID")

    def mutate(self, info, id):
        try:
            obj = Account.objects.get(pk=id)
            obj.picture = None
            obj.save()

            return DeleteAccountPictureMutation(ok=True)
        except Account.DoesNotExist:
            return DeleteAccountPictureMutation(ok=False)


class AccountMutation:
    _delete_account_picture_mutation = DeleteAccountPictureMutation.Field()
