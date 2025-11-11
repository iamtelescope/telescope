from rest_framework import serializers

from telescope.models import Connection, ConnectionRoleBinding
from telescope.serializers.rbac import UserSerializer, GroupSerializer

SUPPORTED_KINDS = {"clickhouse", "docker", "kubernetes"}


class SerializeErrorMsg:
    DB_SUPPORTED_ONLY_CLICK = "Only these kinds are supported: " + ", ".join(
        SUPPORTED_KINDS
    )


class ConnectionSerializer(serializers.ModelSerializer):
    permissions = serializers.ListField(child=serializers.CharField(), required=False)

    class Meta:
        model = Connection
        fields = "__all__"

    def validate_kind(self, value):
        if value not in SUPPORTED_KINDS:
            raise serializers.ValidationError(SerializeErrorMsg.DB_SUPPORTED_ONLY_CLICK)
        return value


class ConnectionListSerializer(serializers.ModelSerializer):
    """Serializer for connection list - excludes data field"""

    permissions = serializers.ListField(child=serializers.CharField(), required=False)

    class Meta:
        model = Connection
        exclude = ["data"]


class ClickhouseConnectionSerializer(serializers.Serializer):
    host = serializers.CharField()
    port = serializers.IntegerField()
    user = serializers.CharField()
    password = serializers.CharField(allow_blank=True)
    ssl = serializers.BooleanField()
    verify = serializers.BooleanField()
    ca_cert = serializers.CharField(allow_blank=True, allow_null=True)
    client_cert = serializers.CharField(allow_blank=True, allow_null=True)
    client_cert_key = serializers.CharField(allow_blank=True, allow_null=True)
    server_host_name = serializers.CharField(allow_blank=True, allow_null=True)
    tls_mode = serializers.CharField(allow_blank=True, allow_null=True)


class DockerConnectionSerializer(serializers.Serializer):
    address = serializers.CharField()


class KubernetesConnectionSerializer(serializers.Serializer):
    kubeconfig = serializers.CharField(
        allow_blank=True,
        required=False,
        help_text="Raw kubeconfig file content",
    )

    def validate(self, data):
        errors = {}
        if not data.get("kubeconfig"):
            errors["kubeconfig"] = "Kubeconfig content is required."
        if errors:
            raise serializers.ValidationError(errors)
        return data

class ConnectionCreateResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=True)


class ConnectionUpdateResponseSerializer(ConnectionCreateResponseSerializer):
    pass


class SubjectSerializer(serializers.Serializer):
    kind = serializers.CharField()
    name = serializers.CharField()


class ConnectionRoleSerializer(serializers.Serializer):
    subject = SubjectSerializer()
    role = serializers.CharField()


class ConnectionRoleBindingSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    group = GroupSerializer()

    class Meta:
        model = ConnectionRoleBinding
        fields = ["user", "group", "connection", "role"]
