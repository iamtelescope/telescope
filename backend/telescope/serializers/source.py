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
            raise serializers.ValidationError("only clickhouse kind is supported atm")
        return value

    def to_internal_value(self, data):
        data["default_chosen_fields"] = [
            x.strip() for x in data["default_chosen_fields"].split(",") if x.strip()
        ]
        return super().to_internal_value(data)

    def validate_slug(self, value):
        if Source.objects.filter(slug=value).exists():
            raise serializers.ValidationError("source with that slug already exist")
        if value.startswith("-"):
            raise serializers.ValidationError("should not starts with dash")
        if value.endswith("-"):
            raise serializers.ValidationError("should not ends with dash")
        return value

    def validate_default_chosen_fields(self, value):
        if not value:
            raise serializers.ValidationError("This field may not be blank")
        return value

    def validate_severity_field(self, value):
        if value is None:
            return ""
        return value

    def validate(self, data):
        errors = {}

        # for field_name in ["time_field", "uniq_field", "severity_field"]:
        for field_name in ["time_field", "severity_field"]:
            value = data[field_name]
            if value and value not in data["fields"]:
                errors[field_name] = f"field {value} was not found in fields list"
            elif field_name == "time_field":
                if "datetime" not in data["fields"][value]["type"].lower():
                    errors["time_field"] = f"filed should have corret type"

        chosen_errors = []
        for field_name in data["default_chosen_fields"]:
            if field_name not in data["fields"]:
                chosen_errors.append(f"field {field_name} was not found in fields list")

        if chosen_errors:
            errors["default_chosen_fields"] = ", ".join(chosen_errors)

        if errors:
            raise serializers.ValidationError(errors)

        return data


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
                raise serializers.ValidationError(
                    "insuffisient permissions to use source raw queries"
                )
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
