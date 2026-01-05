from django.contrib.auth import views, logout
from django.contrib.auth.models import User
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views import View
from django.conf import settings

from allauth.socialaccount.models import SocialAccount
from rest_framework.response import Response
from rest_framework.views import APIView

from telescope.serializers.auth import (
    WhoAmISerializer,
    APITokenSerializer,
    APITokensDeleteRequestSerializer,
    APITokenCreateRequestSerializer,
)
from telescope.response import UIResponse
from telescope.models import APIToken
from telescope.auth.forms import LoginForm, SuperuserForm
from telescope.rbac.manager import RBACManager

rbac_manager = RBACManager()


class LoginView(views.LoginView):
    template_name = "forms/login.html"
    form_class = LoginForm
    next_page = settings.LOGIN_REDIRECT_URL
    extra_context = {
        "base_url": settings.BASE_URL or "",
        "github_enabled": settings.CONFIG["auth"]["providers"]["github"]["enabled"],
        "okta_enabled": settings.CONFIG["auth"]["providers"]["okta"]["enabled"],
        "force_auth_provider": settings.CONFIG["auth"]["force_auth_provider"],
    }

    def dispatch(self, request, *args, **kwargs):
        if settings.CONFIG["auth"]["enable_testing_auth"]:
            return redirect("/")
        if User.objects.filter(is_superuser=True).count() == 0:
            return redirect("/setup")
        return super().dispatch(request, *args, **kwargs)


class LocalLoginView(views.LoginView):
    template_name = "forms/login.html"
    form_class = LoginForm
    next_page = settings.LOGIN_REDIRECT_URL

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "base_url": settings.BASE_URL or "",
                "github_enabled": settings.CONFIG["auth"]["providers"]["github"][
                    "enabled"
                ],
                "okta_enabled": settings.CONFIG["auth"]["providers"]["okta"]["enabled"],
                "force_auth_provider": None,
            }
        )
        return context

    def dispatch(self, request, *args, **kwargs):
        if settings.CONFIG["auth"]["enable_testing_auth"]:
            return redirect("/")
        if User.objects.filter(is_superuser=True).count() == 0:
            return redirect("/setup")

        secret_path = kwargs.get("secret_path")
        configured_secret = settings.CONFIG["auth"].get("local_login_secret_path")

        if not configured_secret or secret_path != configured_secret:
            return redirect("/login")

        return super().dispatch(request, *args, **kwargs)


class LogoutView(View):
    template_name = "forms/logout.html"

    def get(self, request):
        if settings.CONFIG["auth"]["enable_testing_auth"]:
            return redirect("/")
        return render(
            request, "forms/logout.html", {"base_url": settings.BASE_URL or ""}
        )

    def post(self, request):
        logout(request)
        return redirect("/")


class SuperuserView(View):
    def dispatch(self, request, *args, **kwargs):
        if settings.CONFIG["auth"]["enable_testing_auth"]:
            return redirect("/")
        if User.objects.filter(is_superuser=True).count() > 0:
            return redirect("/login")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        form = SuperuserForm
        return render(
            request,
            "forms/superuser.html",
            {"form": form, "base_url": settings.BASE_URL or ""},
        )

    def post(self, request):
        form = SuperuserForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = User.objects.create(
                        username=form.cleaned_data["username"],
                        is_superuser=True,
                    )
                    user.set_password(form.cleaned_data["password"])
                    user.save()
            except Exception as err:
                form.add_error(f"Unhandled exception: {err}")
            else:
                return redirect("/login")
        return render(
            request,
            "forms/superuser.html",
            {"form": form, "base_url": settings.BASE_URL or ""},
        )


class WhoAmIView(APIView):
    @method_decorator(login_required)
    def get(self, request):
        response = UIResponse()
        result = SocialAccount.objects.filter(user=request.user)
        social_account = None
        if result:
            social_account = result[0]

        data = {
            "id": request.user.id,
            "username": request.user.username,
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "permissions": list(rbac_manager.get_user_global_permissions(request.user)),
            "type": "local",
            "avatar_url": "",
        }
        if social_account:
            user_data = social_account.get_provider_account().get_user_data()
            data["type"] = social_account.provider

            if social_account.provider == "github":
                data["username"] = user_data["login"]
                data["avatar_url"] = user_data["avatar_url"]
            elif social_account.provider == "okta":
                data["username"] = user_data.get(
                    "preferred_username", user_data.get("email", request.user.username)
                )
                data["avatar_url"] = user_data.get("picture", "")
        serializer = WhoAmISerializer(data=data)
        if not serializer.is_valid():
            response.mark_failed(str(serializer.errors))
        else:
            response.data = serializer.data
        return Response(response.as_dict())


class UserAPITokenView(APIView):
    @method_decorator(login_required)
    def get(self, request):
        response = UIResponse()
        tokens = APIToken.objects.filter(user=request.user)
        serializer = APITokenSerializer(tokens, many=True)

        response.data = serializer.data
        return Response(response.as_dict())

    @method_decorator(login_required)
    def post(selfself, request):
        response = UIResponse()
        try:
            serializer = APITokenCreateRequestSerializer(data=request.data)
            if not serializer.is_valid():
                response.validation["result"] = False
                response.validation["columns"] = serializer.errors
                response.mark_failed(str(serializer.errors))
            else:
                with transaction.atomic():
                    token = APIToken.create(
                        user=request.user, name=serializer.data["name"]
                    )
                    response.add_msg(f"API token {token.name} has been created")
        except Exception as err:
            response.mark_failed("unhandled exception: {}".format(err))

        return Response(response.as_dict())


class UserAPITokensDeleteView(APIView):
    @method_decorator(login_required)
    def post(self, request):
        response = UIResponse()
        serializer = APITokensDeleteRequestSerializer(data=request.data)
        try:
            if not serializer.is_valid():
                response.mark_failed(str(serializer.errors))
            else:
                with transaction.atomic():
                    for token in APIToken.objects.filter(
                        user=request.user, token__in=serializer.data["tokens"]
                    ):
                        name = token.name
                        token.delete()
                        response.add_msg(f"API token {name} has been deleted")
        except Exception as err:
            response.mark_failed("unhandled exception: {}".format(err))

        return Response(response.as_dict())
