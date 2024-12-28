from django.conf import settings
from django.dispatch import receiver
from django.core.exceptions import PermissionDenied

from allauth.socialaccount.signals import (
    pre_social_login,
)
import requests


@receiver([pre_social_login])
def check_github_organization_membership(request, sociallogin, **kwargs):
    if not settings.CONFIG["auth"]["providers"]["github"]["enabled"]:
        return

    if sociallogin.account.provider != "github":
        return

    if not settings.CONFIG["auth"]["providers"]["github"]["organizations"]:
        return

    token = sociallogin.token.token
    headers = {"Authorization": f"token {token}"}
    membership_found = False

    for org in settings.CONFIG["auth"]["providers"]["github"]["organizations"]:
        url = f"https://api.github.com/user/memberships/orgs/{org}"

        response = requests.get(url, headers=headers)

        if response.status_code == 200 or response.json().get("state") == "active":
            membership_found = True
            break
    if not membership_found:
        raise PermissionDenied(
            "You must be a member of the required GitHub organization to log in."
        )
