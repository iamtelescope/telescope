from typing import List
from django.contrib.auth.models import User, Group

from rest_framework import serializers

from telescope.models import Source, SavedView, SourceRoleBinding
from telescope.utils import parse_time
from telescope.columns import ParsedColumn, parse_columns
from telescope.fetchers import get_fetchers
from telescope.rbac.manager import RBACManager

rbac_manager = RBACManager()
from telescope.rbac import permissions
from telescope.constants import VIEW_SCOPE_SOURCE, VIEW_SCOPE_PERSONAL


from telescope.utils import (
    ALLOWED_TIME_COLUMN_TYPES,
    ALLOWED_DATE_COLUMN_TYPES,
    convert_to_base_ch,
)

SUPPORTED_KINDS = {"clickhouse", "docker", "kubernetes"}


class SerializeErrorMsg:
    EMPTY_COLUMN = "This field may not be blank"
    SLUG_SOURCE_EXIST = "Source with that slug already exist"
    SLUG_START_WITH_DASH = "Should not starts with dash"
    SLUG_END_WITH_DASH = "Should not ends with dash"
    DB_SUPPORTED_ONLY_CLICK = "Only these kinds are supported: " + ", ".join(
        SUPPORTED_KINDS
    )
    TIME_COLUMN_TYPE = "Column should have a valid time-related type"
    DATE_COLUMN_TYPE = "Column should have a valid date-related type"
    RAW_QUERIES_PERMISSIONS = "Insufficient permissions to use source raw queries"
    RAW_QUERIES_NOT_SUPPORTED = "This source does not support raw queries"


class SourceAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Source
        fields = "__all__"


class SourceSerializer(serializers.ModelSerializer):
    permissions = serializers.ListField(child=serializers.CharField())
    connection_id = serializers.IntegerField(source="conn_id", read_only=True)

    class Meta:
        model = Source
        exclude = ["conn"]


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name"]


class SourceSavedViewSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    permissions = serializers.ListField(child=serializers.CharField())
    kind = serializers.CharField()

    class Meta:
        model = SavedView
        fields = "__all__"


class SourceSavedViewScopeSerializer(serializers.Serializer):
    scope = serializers.ChoiceField(
        required=True,
        choices=[
            (VIEW_SCOPE_PERSONAL, VIEW_SCOPE_PERSONAL),
            (VIEW_SCOPE_SOURCE, VIEW_SCOPE_SOURCE),
        ],
    )


class NewSourceSavedViewSerializer(serializers.Serializer):
    name = serializers.CharField(required=True, max_length=255)
    description = serializers.CharField(max_length=4096, allow_blank=True)
    shared = serializers.BooleanField()
    data = serializers.JSONField()


class UpdateSourceSavedViewSerializer(
    NewSourceSavedViewSerializer, SourceSavedViewScopeSerializer
):
    pass


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name"]


class SubjectSerializer(serializers.Serializer):
    kind = serializers.CharField()
    name = serializers.CharField()


class SourceRoleSerializer(serializers.Serializer):
    subject = SubjectSerializer()
    role = serializers.CharField()


class SourceRoleBindingSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    group = GroupSerializer()

    class Meta:
        model = SourceRoleBinding
        fields = ["user", "group", "source", "role"]


class ConnectionSerializer(serializers.Serializer):
    kind = serializers.CharField()
    data = serializers.JSONField()


class ClickhouseConnectionSerializer(serializers.Serializer):
    host = serializers.CharField()
    port = serializers.IntegerField()
    user = serializers.CharField()
    password = serializers.CharField(allow_blank=True)
    database = serializers.CharField()
    table = serializers.CharField()
    ssl = serializers.BooleanField()
    verify = serializers.BooleanField()
    ca_cert = serializers.CharField(allow_blank=True)
    certfile = serializers.CharField(allow_blank=True)
    keyfile = serializers.CharField(allow_blank=True)
    ssl_version = serializers.CharField(allow_blank=True)
    ciphers = serializers.CharField(allow_blank=True)
    server_hostname = serializers.CharField(allow_blank=True)
    alt_hosts = serializers.CharField(allow_blank=True)


class DockerConnectionSerializer(serializers.Serializer):
    address = serializers.CharField()


class KubernetesConnectionSerializer(serializers.Serializer):
    kubeconfig = serializers.CharField(
        required=True,
        help_text="Raw kubeconfig file content or local file path",
    )
    kubeconfig_hash = serializers.CharField(
        required=True, help_text="SHA256 hash of kubeconfig content or file path"
    )
    kubeconfig_is_local = serializers.BooleanField(
        required=True, help_text="Whether kubeconfig is a local file path"
    )

    def validate(self, data):
        errors = {}
        if not data.get("kubeconfig"):
            errors["kubeconfig"] = "Kubeconfig content or file path is required."
        if not data.get("kubeconfig_hash"):
            errors["kubeconfig_hash"] = "Kubeconfig hash is required."
        if data.get("kubeconfig_is_local") is None:
            errors["kubeconfig_is_local"] = "Local file path indicator is required."
        if errors:
            raise serializers.ValidationError(errors)
        return data


class GetSourceSchemaClickhouseSerializer(serializers.Serializer):
    connection_id = serializers.IntegerField()
    database = serializers.CharField()
    table = serializers.CharField()


class GetSourceSchemaDockerSerializer(serializers.Serializer):
    connection_id = serializers.IntegerField()


class GetSourceSchemaKubernetesSerializer(serializers.Serializer):
    connection_id = serializers.IntegerField()
    namespace = serializers.CharField(required=False, allow_blank=True)


class SourceColumnSerializer(serializers.Serializer):
    display_name = serializers.CharField(allow_blank=True)
    type = serializers.CharField()
    autocomplete = serializers.BooleanField()
    suggest = serializers.BooleanField()
    jsonstring = serializers.BooleanField()
    group_by = serializers.BooleanField()
    values = serializers.ListField(child=serializers.CharField())

    def to_internal_value(self, data):
        if isinstance(data["values"], str):
            data["values"] = [x.strip() for x in data["values"].split(",") if x.strip()]
        return super().to_internal_value(data)


class SourceKindSerializer(serializers.Serializer):
    kind = serializers.CharField()

    def validate_kind(self, value):
        if value not in SUPPORTED_KINDS:
            raise serializers.ValidationError(SerializeErrorMsg.DB_SUPPORTED_ONLY_CLICK)
        return value


class SourceContextColumnDataSerializer(serializers.Serializer):
    column = serializers.CharField()
    params = serializers.DictField(required=False, default=dict)


class NewBaseSourceSerializer(serializers.Serializer):
    SEVERITY_COLUMN_NAME = "severity_column"
    TIME_COLUMN_NAME = "time_column"
    DATE_COLUMN_NAME = "date_column"
    DEFAULT_CHOSEN_COLUMNS_NAME = "default_chosen_columns"

    slug = serializers.SlugField(max_length=64, required=True)
    name = serializers.CharField(max_length=64)
    description = serializers.CharField(allow_blank=True)

    time_column = serializers.CharField()
    date_column = serializers.CharField(allow_blank=True, allow_null=True, default="")
    severity_column = serializers.CharField(allow_blank=True, allow_null=True)
    default_chosen_columns = serializers.ListField(child=serializers.CharField())
    execute_query_on_open = serializers.BooleanField(default=True)
    columns = serializers.DictField(child=SourceColumnSerializer())
    connection = serializers.JSONField()

    def validate_slug(self, value):
        if Source.objects.filter(slug=value).exists():
            raise serializers.ValidationError(SerializeErrorMsg.SLUG_SOURCE_EXIST)
        if value.startswith("-"):
            raise serializers.ValidationError(SerializeErrorMsg.SLUG_START_WITH_DASH)
        if value.endswith("-"):
            raise serializers.ValidationError(SerializeErrorMsg.SLUG_END_WITH_DASH)
        return value

    def to_internal_value(self, data):
        data[self.DEFAULT_CHOSEN_COLUMNS_NAME] = [
            x.strip()
            for x in data[self.DEFAULT_CHOSEN_COLUMNS_NAME].split(",")
            if x.strip()
        ]
        return super().to_internal_value(data)

    def type_validate_default_chosen_columns(self, data):
        chosen_errors = []
        value = data[self.DEFAULT_CHOSEN_COLUMNS_NAME]
        if not value:
            raise serializers.ValidationError(SerializeErrorMsg.EMPTY_COLUMN)

        for column_name in data[self.DEFAULT_CHOSEN_COLUMNS_NAME]:
            if column_name not in data["columns"]:
                chosen_errors.append(
                    f"column {column_name} was not found in columns list"
                )

        errors = {}
        if chosen_errors:
            errors[self.DEFAULT_CHOSEN_COLUMNS_NAME] = ", ".join(chosen_errors)

        return errors

    def type_validate_severity_column(self, data):
        value = data[self.SEVERITY_COLUMN_NAME]
        errors = {}

        if value is None:
            raise serializers.ValidationError(SerializeErrorMsg.EMPTY_COLUMN)
        if value and value not in data["columns"]:
            errors[self.SEVERITY_COLUMN_NAME] = (
                f"column {value} was not found in columns list"
            )
        return errors

    def type_validate_time_column(self, data):
        value = data.get(self.TIME_COLUMN_NAME)
        errors = {}

        if not value:
            raise ValueError(SerializeErrorMsg.EMPTY_COLUMN)

        column_type = convert_to_base_ch(
            data["columns"].get(value, {}).get("type", "").lower()
        )

        if column_type not in ALLOWED_TIME_COLUMN_TYPES:
            errors[self.TIME_COLUMN_NAME] = SerializeErrorMsg.TIME_COLUMN_TYPE

        return errors

    def type_validate_date_column(self, data):
        value = data.get(self.DATE_COLUMN_NAME)
        errors = {}

        if value:

            column_type = convert_to_base_ch(
                data["columns"].get(value, {}).get("type", "").lower()
            )

            if column_type not in ALLOWED_DATE_COLUMN_TYPES:
                errors[self.TIME_COLUMN_NAME] = SerializeErrorMsg.DATE_COLUMN_TYPE

        return errors

    def validate(self, data):
        errors = {}
        errors.update(self.type_validate_severity_column(data))
        errors.update(self.type_validate_time_column(data))
        errors.update(self.type_validate_date_column(data))
        errors.update(self.type_validate_default_chosen_columns(data))

        if errors:
            raise serializers.ValidationError(errors)

        return data

    def validate_default_chosen_columns(self, value):
        if not value:
            raise serializers.ValidationError(SerializeErrorMsg.EMPTY_COLUMN)
        return value

    def validate_severity_column(self, value):
        if value is None:
            return ""
        return value


class ClickhouseSourceDataSerializer(serializers.Serializer):
    database = serializers.CharField(required=True)
    table = serializers.CharField(required=True)
    settings = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class DockerSourceDataSerializer(serializers.Serializer):
    pass


class KubernetesSourceDataSerializer(serializers.Serializer):
    namespace_label_selector = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Kubernetes label selector for namespaces (e.g. 'env=prod,team=backend')",
    )
    namespace_field_selector = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Kubernetes field selector for namespaces (e.g. 'metadata.name=default')",
    )
    namespace = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="FlyQL filter for namespaces (applied after K8s API filtering)",
    )


class NewDockerSourceSerializer(NewBaseSourceSerializer):
    data = DockerSourceDataSerializer(required=False, default=dict)


class NewKubernetesSourceSerializer(NewBaseSourceSerializer):
    data = KubernetesSourceDataSerializer(required=False, default=dict)
    execute_query_on_open = serializers.BooleanField(default=False)


class UpdateDockerSourceSerializer(NewDockerSourceSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.required = False

    def validate_slug(self, value):
        return value


class UpdateKubernetesSourceSerializer(NewKubernetesSourceSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.required = False

    def validate_slug(self, value):
        return value


class NewClickhouseSourceSerializer(NewBaseSourceSerializer):
    data = ClickhouseSourceDataSerializer(required=True)


class UpdateClickhouseSourceSerializer(NewClickhouseSourceSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.required = False

    def validate_slug(self, value):
        return value


class SourceCreateResponseSerializer(serializers.Serializer):
    slug = serializers.SlugField(max_length=64, required=True)


class SourceUpdateResponseSerializer(SourceCreateResponseSerializer):
    pass


class SourceAutocompleteRequestSerializer(serializers.Serializer):
    column = serializers.CharField()
    value = serializers.CharField(allow_blank=True)
    _from = serializers.CharField()
    to = serializers.CharField()

    def get_fields(self):
        fields = super().get_fields()
        _from = fields.pop("_from")
        fields["from"] = _from
        return fields

    def validate_from(self, value):
        value, error = parse_time(value)
        if error:
            raise serializers.ValidationError(error)
        return value

    def validate_to(self, value):
        value, error = parse_time(value)
        if error:
            raise serializers.ValidationError(error)
        return value


class SourceDataRequestSerializer(serializers.Serializer):
    columns = serializers.CharField()
    query = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    raw_query = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    _from = serializers.CharField()
    to = serializers.CharField()
    limit = serializers.IntegerField()
    context_columns = serializers.JSONField(allow_null=True, required=False)

    def get_fields(self):
        fields = super().get_fields()
        _from = fields.pop("_from")
        fields["from"] = _from
        return fields

    def validate_from(self, value):
        value, error = parse_time(value)
        if error:
            raise serializers.ValidationError(error)
        return value

    def validate_to(self, value):
        value, error = parse_time(value)
        if error:
            raise serializers.ValidationError(error)
        return value

    def validate_columns(self, value: str) -> List[ParsedColumn]:
        try:
            value = parse_columns(self.context["source"], value)
        except ColumnsParserError as err:
            raise serializers.ValidationError(err.message)
        return value

    def validate_query(self, value):
        if not value:
            return ""
        fetcher = get_fetchers()[self.context["source"].kind]
        result, help_text = fetcher.validate_query(self.context["source"], value)
        if not result:
            raise serializers.ValidationError(help_text)
        return value

    def validate_context_columns(self, value):
        source = self.context["source"]
        if source.context_columns:
            for column_name in value.keys():
                if column_name not in source.context_columns:
                    raise serializers.ValidationError(
                        f"unknown context column: {column_name}"
                    )
        return value

    def validate(self, data):
        if data.get("raw_query"):
            if not self.context["source"].support_raw_query:
                raise serializers.ValidationError(
                    SerializeErrorMsg.RAW_QUERIES_NOT_SUPPORTED
                )
            if not rbac_manager.user_has_source_permissions(
                self.context["user"],
                source_slug=self.context["source"].slug,
                required_permissions=[permissions.Source.RAW_QUERY.value],
            ):
                raise serializers.ValidationError(
                    SerializeErrorMsg.RAW_QUERIES_PERMISSIONS
                )
        return data


class SourceGraphDataRequestSerializer(SourceDataRequestSerializer):
    group_by = serializers.CharField(allow_blank=True, required=False)

    def __init__(self, *args, **kwargs):
        super(SourceGraphDataRequestSerializer, self).__init__(*args, **kwargs)
        self.fields.pop("columns", None)
        self.fields.pop("limit", None)

    def validate_group_by(self, value: str) -> List[ParsedColumn]:
        try:
            value = parse_columns(self.context["source"], value)
        except ColumnsParserError as err:
            raise serializers.ValidationError(err.message)
        return value


class SourceDataAndGraphDataRequestSerializer(serializers.Serializer):
    """Serializer for combined data and graph data requests"""

    columns = serializers.CharField()
    query = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    raw_query = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    _from = serializers.CharField()
    to = serializers.CharField()
    limit = serializers.IntegerField()
    group_by = serializers.CharField(allow_blank=True, required=False)
    context_columns = serializers.JSONField(allow_null=True, required=False)

    def get_fields(self):
        fields = super().get_fields()
        _from = fields.pop("_from")
        fields["from"] = _from
        return fields

    def validate_from(self, value):
        from telescope.utils import parse_time

        value, error = parse_time(value)
        if error:
            raise serializers.ValidationError(error)
        return value

    def validate_to(self, value):
        from telescope.utils import parse_time

        value, error = parse_time(value)
        if error:
            raise serializers.ValidationError(error)
        return value

    def validate_columns(self, value: str) -> List[ParsedColumn]:
        try:
            value = parse_columns(self.context["source"], value)
        except ColumnsParserError as err:
            raise serializers.ValidationError(err.message)
        return value

    def validate_group_by(self, value: str) -> List[ParsedColumn]:
        if not value:
            return []
        try:
            value = parse_columns(self.context["source"], value)
        except ColumnsParserError as err:
            raise serializers.ValidationError(err.message)
        return value

    def validate_query(self, value):
        if not value:
            return ""
        from telescope.fetchers import get_fetchers

        fetcher = get_fetchers()[self.context["source"].kind]
        result, help_text = fetcher.validate_query(self.context["source"], value)
        if not result:
            raise serializers.ValidationError(help_text)
        return value

    def validate_context_columns(self, value):
        source = self.context["source"]
        if source.context_columns:
            for column_name in value.keys():
                if column_name not in source.context_columns:
                    raise serializers.ValidationError(
                        f"unknown context column: {column_name}"
                    )
        return value

    def validate(self, data):
        if data.get("raw_query"):
            from telescope.rbac.manager import RBACManager
            from telescope.rbac import permissions

            rbac_manager = RBACManager()

            if not self.context["source"].support_raw_query:
                raise serializers.ValidationError(
                    SerializeErrorMsg.RAW_QUERIES_NOT_SUPPORTED
                )
            if not rbac_manager.user_has_source_permissions(
                self.context["user"],
                source_slug=self.context["source"].slug,
                required_permissions=[permissions.Source.RAW_QUERY.value],
            ):
                raise serializers.ValidationError(
                    SerializeErrorMsg.RAW_QUERIES_PERMISSIONS
                )
        return data
