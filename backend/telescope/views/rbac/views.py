from collections import defaultdict

from django.db import transaction
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers

from telescope.response import UIResponse
from telescope.rbac.roles import ROLES
from telescope.rbac.helpers import grant_global_role, revoke_global_role
from telescope.rbac import permissions
from telescope.auth.decorators import global_permission_required
from telescope.models import GlobalRoleBinding
from telescope.serializers.rbac import (
    UserGroupSerializer,
    UserSerializer,
    SimpleUserSerializer,
    SimpleGroupSerializer,
    GroupUserSerializer,
    GroupSerializer,
    NewGroupSerializer,
    UpdateGroupSerializer,
)


class RoleView(APIView):
    @method_decorator(login_required)
    @method_decorator(
        global_permission_required([permissions.Global.MANAGE_RBAC.value])
    )
    def get(self, request, kind=None, name=None):
        response = UIResponse()
        data = []

        try:
            result = defaultdict(dict)

            for _type, roles in ROLES.items():
                for role_name, permissions in roles.items():
                    result[_type][role_name] = {
                        "permissions": permissions,
                        "users": 0,
                        "groups": 0,
                        "name": role_name,
                        "type": _type,
                    }

            for bind in GlobalRoleBinding.objects.all():
                if bind.user_id is not None:
                    result["global"][bind.role]["users"] += 1
                elif bind.group_id is not None:
                    result["global"][bind.role]["groups"] += 1

            for _type, roles in result.items():
                for role_name, role_data in roles.items():
                    data.append(role_data)

            if kind is not None and name is not None:
                result = list(
                    filter(
                        lambda role: role["type"] == kind and role["name"] == name, data
                    )
                )
                if not result:
                    response.mark_failed(
                        f"role of type {kind} and name {name} does not exist"
                    )
                else:
                    data = result[0]

        except Exception as err:
            response.mark_failed(f"failed to get roles: {err}")
        else:
            response.data = data

        return Response(response.as_dict())


class GroupView(APIView):
    @method_decorator(login_required)
    @method_decorator(
        global_permission_required([permissions.Global.MANAGE_RBAC.value])
    )
    def get(self, request, pk=None):
        response = UIResponse()
        try:
            if pk is None:
                groups = Group.objects.prefetch_related("user_set").all()
                serializer = GroupSerializer(groups, many=True)
            else:
                group = Group.objects.prefetch_related("user_set").get(pk=pk)
                serializer = GroupSerializer(group)
        except Exception as err:
            response.mark_failed(f"failed to get groups: {err}")
        else:
            response.data = serializer.data
        return Response(response.as_dict())

    @method_decorator(login_required)
    @method_decorator(
        global_permission_required([permissions.Global.MANAGE_RBAC.value])
    )
    def post(self, request):
        response = UIResponse()
        try:
            serializer = NewGroupSerializer(data=request.data)
            if not serializer.is_valid():
                response.validation["result"] = False
                response.validation["fields"] = serializer.errors
            else:
                group = serializer.save()
                response.data = {"id": group.pk}
        except Exception as err:
            response.mark_failed(f"failed to create group: {err}")
        return Response(response.as_dict())

    @method_decorator(login_required)
    @method_decorator(
        global_permission_required([permissions.Global.MANAGE_RBAC.value])
    )
    def patch(self, request, pk):
        response = UIResponse()
        try:
            group = Group.objects.get(id=pk)
            serializer = UpdateGroupSerializer(data=request.data)
            if not serializer.is_valid():
                response.validation["result"] = False
                response.validation["fields"] = serializer.errors
            else:
                group.name = serializer.data["name"]
                group.save()
        except Exception as err:
            response.mark_failed(f"failed to add user to group: {err}")
        return Response(response.as_dict())

    @method_decorator(login_required)
    @method_decorator(
        global_permission_required([permissions.Global.MANAGE_RBAC.value])
    )
    def delete(self, request, pk):
        response = UIResponse()

        try:
            with transaction.atomic():
                Group.objects.get(pk=pk).delete()
        except Exception as err:
            response.mark_failed(f"failed to delete group: {err}")
        return Response(response.as_dict())


class GroupAddUsersView(APIView):
    @method_decorator(login_required)
    @method_decorator(
        global_permission_required([permissions.Global.MANAGE_RBAC.value])
    )
    def post(self, request, pk):
        response = UIResponse()
        try:
            with transaction.atomic():
                group = Group.objects.get(pk=pk)
                for user in User.objects.filter(id__in=request.data["ids"]):
                    group.user_set.add(user)
                group.save()
        except Exception as err:
            response.mark_failed(f"failed to add user to group: {err}")
        else:
            response.add_msg("Users has been added to group")
            return Response(response.as_dict())


class GroupRemoveUsersView(APIView):
    @method_decorator(login_required)
    @method_decorator(
        global_permission_required([permissions.Global.MANAGE_RBAC.value])
    )
    def post(self, request, pk):
        response = UIResponse()
        try:
            with transaction.atomic():
                group = Group.objects.get(pk=pk)
                for user in User.objects.filter(id__in=request.data["ids"]):
                    group.user_set.remove(user)
                    group.save()
        except Exception as err:
            response.mark_failed(f"failed to remove users from group: {err}")
        else:
            response.add_msg("Users has been removed from group")
        return Response(response.as_dict())


class GroupGrantRoleView(APIView):
    @method_decorator(login_required)
    @method_decorator(
        global_permission_required([permissions.Global.MANAGE_RBAC.value])
    )
    def post(self, request, pk):
        response = UIResponse()
        if request.data["role"] not in ROLES["global"]:
            response.mark_failed(f"Unknown global role: {request.data['role']}")
        else:
            try:
                grant_global_role(request.data["role"], group=Group.objects.get(pk=pk))
            except Exception as err:
                response.mark_failed(f"failed to grant role: {err}")
            else:
                response.add_msg("Role has been granted")
        return Response(response.as_dict())


class GroupRevokeRoleView(APIView):
    @method_decorator(login_required)
    @method_decorator(
        global_permission_required([permissions.Global.MANAGE_RBAC.value])
    )
    def post(self, request, pk):
        response = UIResponse()
        if request.data["role"] not in ROLES["global"]:
            response.mark_failed(f"Unknown global role: {request.data['role']}")
        else:
            try:
                revoke_global_role(request.data["role"], group=Group.objects.get(pk=pk))
            except Exception as err:
                response.mark_failed(f"failed to grant role: {err}")
            else:
                response.add_msg("Role has been granted")
        return Response(response.as_dict())


class UserView(APIView):
    @method_decorator(login_required)
    @method_decorator(
        global_permission_required([permissions.Global.MANAGE_RBAC.value])
    )
    def get(self, request, pk=None):
        response = UIResponse()
        try:
            if pk is None:
                users = User.objects.prefetch_related("groups").all()
                serializer = UserSerializer(users, many=True)
        except Exception as err:
            response.mark_failed(f"failed to remove users from group: {err}")
        else:
            response.add_msg("Users has been removed from group")
        response.data = serializer.data
        return Response(response.as_dict())


class SimpleUserListView(APIView):
    @method_decorator(login_required)
    @method_decorator(
        global_permission_required([permissions.Global.MANAGE_RBAC.value])
    )
    def get(self, request):
        response = UIResponse()
        users = User.objects.all()
        serializer = SimpleUserSerializer(users, many=True)
        response.data = serializer.data
        return Response(response.as_dict())


class SimpleGroupListView(APIView):
    @method_decorator(login_required)
    @method_decorator(
        global_permission_required([permissions.Global.MANAGE_RBAC.value])
    )
    def get(self, request):
        response = UIResponse()
        groups = Group.objects.all()
        serializer = SimpleGroupSerializer(groups, many=True)
        response.data = serializer.data
        return Response(response.as_dict())
