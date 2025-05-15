from telescope.models import APIToken

from rest_framework import serializers


class WhoAmISerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    first_name = serializers.CharField(allow_blank=True)
    last_name = serializers.CharField(allow_blank=True)
    type = serializers.CharField()
    avatar_url = serializers.CharField(allow_blank=True)
    permissions = serializers.ListField(child=serializers.CharField())


class APITokenSerializer(serializers.ModelSerializer):
    created = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ")

    class Meta:
        model = APIToken
        fields = "__all__"


class APITokensDeleteRequestSerializer(serializers.Serializer):
    tokens = serializers.ListField(child=serializers.CharField())


class APITokenCreateRequestSerializer(serializers.Serializer):
    name = serializers.CharField()
