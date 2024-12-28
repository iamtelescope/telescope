from django.contrib.auth.models import User, Group

from rest_framework import serializers


class UserGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["name"]


class UserSerializer(serializers.ModelSerializer):
    groups = UserGroupSerializer(many=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "last_login",
            "groups",
            "is_active",
        ]


class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name"]


class SimpleGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["name"]


class GroupUserSerializer(UserSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name"]


class GroupSerializer(serializers.ModelSerializer):
    user_count = serializers.SerializerMethodField()
    users = GroupUserSerializer(source="user_set", many=True)
    roles = serializers.SerializerMethodField()

    class Meta:
        model = Group
        exclude = ["permissions"]

    def get_user_count(self, obj):
        return obj.user_set.count()

    def get_roles(self, obj):
        return [g.role for g in obj.globalrolebinding_set.all()]


class NewGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        exclude = ["permissions"]


class UpdateGroupSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=64)

    class Meta:
        model = Group
        fields = ["name"]
