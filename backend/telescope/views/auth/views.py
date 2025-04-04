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

from telescope.response import UIResponse
from telescope.auth.forms import LoginForm, SuperuserForm
from telescope.rbac.helpers import get_user_global_permissions


class LoginView(views.LoginView):
    template_name = "forms/login.html"
    form_class = LoginForm
    next_page = "/"
    extra_context = {
        "github_enabled": settings.CONFIG["auth"]["providers"]["github"]["enabled"],
        "force_github_auth": settings.CONFIG["auth"]["force_github_auth"],
    }

    def dispatch(self, request, *args, **kwargs):
        if settings.CONFIG["auth"]["enable_testing_auth"]:
            return redirect("/")
        if User.objects.filter(is_superuser=True).count() == 0:
            return redirect("/setup")
        return super().dispatch(request, *args, **kwargs)


class LogoutView(View):
    template_name = "forms/logout.html"

    def get(self, request):
        if settings.CONFIG["auth"]["enable_testing_auth"]:
            return redirect("/")
        return render(request, "forms/logout.html")

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
        return render(request, "forms/superuser.html", {"form": form})

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
        return render(request, "forms/superuser.html", {"form": form})


class WhoAmIView(APIView):
    @method_decorator(login_required)
    def get(self, request):
        response = UIResponse()
        result = SocialAccount.objects.filter(user=request.user)
        social_account = None
        if result:
            social_account = result[0]
        response.data = {
            "username": request.user.username,
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "permissions": get_user_global_permissions(request.user),
            "type": "local",
            "avatar_url": None,
        }
        if social_account and social_account.provider == "github":
            user_data = social_account.get_provider_account().get_user_data()
            response.data["type"] = social_account.provider
            response.data["username"] = user_data["login"]
            response.data["avatar_url"] = user_data["avatar_url"]
        return Response(response.as_dict())
