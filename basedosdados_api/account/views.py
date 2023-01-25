# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from basedosdados_api.account.models import RegistrationToken
from basedosdados_api.account.serializers import UserSerializer


class RegisterView(APIView):

    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        try:
            data = request.data

            first_name = data["first_name"]
            last_name = data["last_name"]
            username = data["username"]
            email = data["email"]
            password = data["password"]
            re_password = data["re_password"]
            registration_token = data["registration_token"]

            try:
                token: RegistrationToken = RegistrationToken.objects.get(
                    token=registration_token
                )
                if not token.active:
                    return Response(
                        {"error": "Token is not active"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except RegistrationToken.DoesNotExist:
                return Response(
                    {"error": "Token is not valid"}, status=status.HTTP_400_BAD_REQUEST
                )

            if password != re_password:
                return Response(
                    {"error": "Passwords do not match"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if len(password) < 8:
                return Response(
                    {"error": "Password must be at least 8 characters long"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if User.objects.filter(username=username).exists():
                return Response(
                    {"error": "Username already exists"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user: User = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
            user.save()

            token.active = False
            token.save()

            if User.objects.filter(username=username).exists():
                return Response(
                    {"success": "User created successfully"},
                    status=status.HTTP_201_CREATED,
                )

            return Response(
                {"error": "Something went wrong when trying to create a new user."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        except:  # noqa
            return Response(
                {"error": "Something went wrong when trying to create a new user."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LoadUserView(APIView):
    def get(self, request, format=None):
        try:
            user = request.user
            user = UserSerializer(user)

            return Response({"user": user.data}, status=status.HTTP_200_OK)

        except:  # noqa
            return Response(
                {"error": "Something went wrong when trying to load the user."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
