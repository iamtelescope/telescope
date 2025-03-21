from typing import List
from django.contrib.auth.models import User, Group

from rest_framework import serializers

from telescope.models import Source, SourceRoleBinding
from telescope.utils import parse_time
from telescope.fields import (
    parse as parse_fields,
    ParserError as FieldsParserError,
    ParsedField,
)
from telescope.fetchers import get_fetchers
from telescope.rbac.helpers import user_has_source_permissions
from telescope.rbac import permissions

from telescope.utils import ALLOWED_TIME_FIELD_TYPES, convert_to_base_ch

class SerializeErrorMsg:
    EMPTY_FIELD = "This field may not be blank"
    SLUG_SOURCE_EXIST = "Source with that slug already exist"
    SLUG_START_WITH_DASH = "Should not starts with dash"
    SLUG_END_WITH_DASH = "Should not ends with dash"
    DB_SUPPORTED_ONLY_CLICK = "Only clickhouse kind is supported atm"
    TIME_FIELD_TYPE = "Field should have a valid time-related type"
    RAW_QUERIES_PERMISSIONS = "Insufficient permissions to use source raw queries"


class SourceAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Source
        fields = "__all__"


class SourceSerializer(serializers.ModelSerializer):
    permissions = serializers.ListField(child=serializers.CharField())

    class Meta:
        model = Source
        exclude = ["connection"]


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name"]


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
    host = serializers.CharField()
    port = serializers.IntegerField()
    user = serializers.CharField()
    password = serializers.CharField(allow_blank=True)
    database = serializers.CharField()
    table = serializers.CharField()
    ssl = serializers.BooleanField()


class SourceWithConnectionSerializer(serializers.ModelSerializer):
    permissions = serializers.ListField(child=serializers.CharField())

    class Meta:
        model = Source
        fields = "__all__"


class SourceFieldSerializer(serializers.Serializer):
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


class NewSourceSerializer(serializers.Serializer):
    SEVERITY_FIELD_NAME = "severity_field"
    TIME_FIELD_NAME = "time_field"
    DEFAULT_CHOSEN_FIELDS_NAME = "default_chosen_fields"

    kind = serializers.CharField()
    slug = serializers.SlugField(max_length=64, required=True)
    name = serializers.CharField(max_length=64)
    description = serializers.CharField(allow_blank=True)
    time_field = serializers.CharField()
    # uniq_field = serializers.CharField()
    severity_field = serializers.CharField(allow_blank=True, allow_null=True)
    default_chosen_fields = serializers.ListField(child=serializers.CharField())
    fields = serializers.DictField(child=SourceFieldSerializer())
    connection = ConnectionSerializer()

    def validate_kind(self, value):
        if value != "clickhouse":
            raise serializers.ValidationError(SerializeErrorMsg.DB_SUPPORTED_ONLY_CLICK)
        return value

    def to_internal_value(self, data):
        data[self.DEFAULT_CHOSEN_FIELDS_NAME] = [
            x.strip() for x in data[self.DEFAULT_CHOSEN_FIELDS_NAME].split(",") if x.strip()
        ]
        return super().to_internal_value(data)

    def type_validate_default_chosen_fields(self, data):
        chosen_errors = []
        value = data[self.DEFAULT_CHOSEN_FIELDS_NAME]
        if not value:
            raise [SerializeErrorMsg.EMPTY_FIELD]

        for field_name in data[self.DEFAULT_CHOSEN_FIELDS_NAME]:
            if field_name not in data["fields"]:
                chosen_errors.append(f"field {field_name} was not found in fields list")

        errors = {}
        if chosen_errors:
            errors[self.DEFAULT_CHOSEN_FIELDS_NAME] = ", ".join(chosen_errors)

        return errors

    def type_validate_severity_field(self, data):
        value = data[self.SEVERITY_FIELD_NAME]
        errors = {}

        if value is None:
            raise SerializeErrorMsg.EMPTY_FIELD
        if value not in data["fields"]:
            errors[self.SEVERITY_FIELD_NAME] = f"field {value} was not found in fields list"
        return errors

    def type_validate_time_field(self, data):
        value = data.get(self.TIME_FIELD_NAME)
        errors = {}

        if not value:
            raise ValueError(SerializeErrorMsg.EMPTY_FIELD)

        field_type = convert_to_base_ch(data["fields"].get(value, {}).get("type", "").lower())

        if field_type not in ALLOWED_TIME_FIELD_TYPES:
            errors[self.TIME_FIELD_NAME] = SerializeErrorMsg.TIME_FIELD_TYPE

        return errors

    def validate(self, data):
        errors = {}
        errors.update(self.type_validate_severity_field(data))
        errors.update(self.type_validate_time_field(data))
        errors.update(self.type_validate_default_chosen_fields(data))

        if errors:
            raise serializers.ValidationError(errors)

        return data

    def validate_slug(self, value):
        if Source.objects.filter(slug=value).exists():
            raise serializers.ValidationError(SerializeErrorMsg.SLUG_SOURCE_EXIST)
        if value.startswith("-"):
            raise serializers.ValidationError(SerializeErrorMsg.SLUG_START_WITH_DASH)
        if value.endswith("-"):
            raise serializers.ValidationError(SerializeErrorMsg.SLUG_END_WITH_DASH)
        return value

    def validate_default_chosen_fields(self, value):
        if not value:
            raise serializers.ValidationError(SerializeErrorMsg.EMPTY_FIELD)
        return value

    def validate_severity_field(self, value):
        if value is None:
            return ""
        return value


class UpdateSourceSerializer(NewSourceSerializer):
    def validate_slug(self, value):
        return value


class SourceAutocompleteRequestSerializer(serializers.Serializer):
    field = serializers.CharField()
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
    fields = serializers.CharField()
    query = serializers.CharField(allow_blank=True)
    raw_query = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    _from = serializers.CharField()
    to = serializers.CharField()
    limit = serializers.IntegerField()

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

    def validate_fields(self, value: str) -> List[ParsedField]:
        try:
            value = parse_fields(self.context["source"], value)
        except FieldsParserError as err:
            raise serializers.ValidationError(err.message)
        return value

    def validate_query(self, value):
        fetcher = get_fetchers()[self.context["source"].kind]
        result, help_text = fetcher.validate_query(self.context["source"], value)
        if not result:
            raise serializers.ValidationError(help_text)
        return value

    def validate(self, data):
        if data.get("raw_query"):
            if not user_has_source_permissions(
                self.context["user"],
                source_slug=self.context["source"].slug,
                required_permissions=[permissions.Source.RAW_QUERY.value],
            ):
                raise serializers.ValidationError(SerializeErrorMsg.RAW_QUERIES_PERMISSIONS)
        return data


class SourceGraphDataRequestSerializer(SourceDataRequestSerializer):
    group_by = serializers.CharField(allow_blank=True, required=False)

    def __init__(self, *args, **kwargs):
        super(SourceGraphDataRequestSerializer, self).__init__(*args, **kwargs)
        self.fields.pop("fields", None)
        self.fields.pop("limit", None)

    def validate_group_by(self, value: str) -> List[ParsedField]:
        try:
            value = parse_fields(self.context["source"], value)
        except FieldsParserError as err:
            raise serializers.ValidationError(err.message)
        return value
