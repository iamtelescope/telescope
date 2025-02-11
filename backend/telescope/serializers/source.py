from django.contrib.auth.models import User, Group

from rest_framework import serializers

from telescope.models import Source, Connection, SourceRoleBinding
from telescope.utils import parse_time
from telescope.fields import parse as parse_fields, ParserError as FieldsParserError
from telescope.query import validate_flyql_query


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
    kind = serializers.CharField()
    host = serializers.CharField()
    port = serializers.IntegerField()
    user = serializers.CharField()
    password = serializers.CharField(allow_blank=True)
    database = serializers.CharField()
    table = serializers.CharField()
    ssl = serializers.BooleanField()


class SourceWithConnectionSerializer(serializers.ModelSerializer):
    permissions = serializers.ListField(child=serializers.CharField())
    connection = ConnectionSerializer()

    class Meta:
        model = Source
        fields = "__all__"


class SourceFieldSerializer(serializers.Serializer):
    display_name = serializers.CharField(allow_blank=True)
    type = serializers.CharField()
    autocomplete = serializers.BooleanField()
    suggest = serializers.BooleanField()
    values = serializers.ListField(child=serializers.CharField())

    def to_internal_value(self, data):
        if isinstance(data["values"], str):
            data["values"] = [x.strip() for x in data["values"].split(",") if x.strip()]
        return super().to_internal_value(data)


class NewSourceSerializer(serializers.Serializer):
    slug = serializers.SlugField(max_length=64, required=True)
    name = serializers.CharField(max_length=64)
    description = serializers.CharField(allow_blank=True)
    time_field = serializers.CharField()
    # uniq_field = serializers.CharField()
    severity_field = serializers.CharField()
    default_chosen_fields = serializers.ListField(child=serializers.CharField())
    fields = serializers.DictField(child=SourceFieldSerializer())
    connection = ConnectionSerializer()

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

    def validate(self, data):
        errors = {}

        # for field_name in ["time_field", "uniq_field", "severity_field"]:
        for field_name in ["time_field", "severity_field"]:
            value = data[field_name]
            if value not in data["fields"]:
                errors[field_name] = f"field {value} was not found in fields list"
            elif field_name == "time_field":
                if not data["fields"][value]["type"].startswith("datetime"):
                    errors["time_field"] = (
                        f"filed should have corret type (e.g. datetime)"
                    )

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

    def validate_fields(self, value):
        try:
            value = parse_fields(self.context["source"], value)
        except FieldsParserError as err:
            raise serializers.ValidationError(err.message)
        return value

    def validate_query(self, value):
        result, help_text = validate_flyql_query(self.context["source"], value)
        if not result:
            raise serializers.ValidationError(help_text)
        return value
