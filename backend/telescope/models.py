import json
from datetime import datetime

from django.db import models
from django.contrib.auth.models import User, Group

from telescope.constants import UTC_ZONE


class AuditEvent(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    username = models.CharField(max_length=255, db_index=True)
    message = models.TextField(null=True, db_index=True)
    type = models.CharField(max_length=32, db_index=True)
    obj_pk = models.CharField(max_length=255, null=True, db_index=True)
    obj_model = models.CharField(max_length=255, null=True, db_index=True)
    obj_action = models.CharField(max_length=255, null=True, db_index=True)
    obj_changes = models.JSONField(null=True)

    @classmethod
    def write(
        self, username, message, type, obj_pk, obj_model, obj_action, obj_changes=None
    ):
        AuditEvent.objects.create(
            username=username,
            message=message,
            type=type,
            obj_pk=obj_pk,
            obj_model=obj_model,
            obj_action=obj_action,
            obj_changes=obj_changes,
        )


class Connection(models.Model):
    name = models.CharField(max_length=128)
    host = models.CharField(max_length=256)
    port = models.IntegerField()
    database = models.CharField(max_length=256)
    table = models.CharField(max_length=256)
    user = models.CharField(max_length=256)
    password = models.CharField(max_length=256)
    ssl = models.BooleanField()
    kind = models.CharField(max_length=32)


class Source(models.Model):
    kind = models.CharField(max_length=32)
    slug = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=64)
    description = models.TextField()
    time_field = models.CharField(max_length=128)
    uniq_field = models.CharField(max_length=128)
    severity_field = models.CharField(max_length=128)
    fields = models.JSONField()
    modifiers = models.JSONField()
    table = models.CharField(max_length=128)
    default_chosen_fields = models.JSONField()
    connection = models.ForeignKey(Connection, on_delete=models.SET_NULL, null=True)

    def __init__(self, *args, **kwargs):
        super(Source, self).__init__(*args, **kwargs)
        self.permissions = set()

    @classmethod
    def create(self, data, username):
        conn = Connection.objects.create(**data.pop("connection"))
        source_data = {"modifiers": [], "connection": conn, "kind": conn.kind}
        for key, value in data.items():
            source_data[key] = value
        source = Source.objects.create(**source_data)
        AuditEvent.write(
            username=username,
            message="Source has been created",
            type="new",
            obj_pk=source.pk,
            obj_model="Source",
            obj_action="create",
            obj_changes=None,
        )
        return source

    @property
    def _record_pseuod_id_field(self):
        return "_____record_pseudo_id"

    @property
    def _fields(self):
        fields = {}
        for key, value in self.fields.items():
            fields[key] = {
                "name": key,
                "type": value["type"],
                "display_name": value.get("display_name"),
                "modifier": value.get("modifier"),
                "values": value.get("values"),
            }
        return fields

    def add_perms(self, perms):
        for perm in perms:
            self.permissions.add(perm)


class SourceRoleBinding(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, null=True)
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    role = models.CharField(max_length=32)


class GlobalRoleBinding(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, null=True)
    role = models.CharField(max_length=32)


class Row:
    def __init__(
        self,
        source,
        selected_fields,
        values,
        timezone=UTC_ZONE,
    ):
        self.source = source
        self.data = {}
        for key, value in zip(selected_fields, values):
            self.data[key] = value

        self.record_id = self.data.get(source.uniq_field) or self.data.get(
            source._record_pseuod_id_field
        )
        self.time = {
            "unixtime": int(self.data[source.time_field].timestamp() * 1000),
            "datetime": datetime.strftime(
                self.data[source.time_field], "%Y-%m-%d %H:%M:%S"
            ),
            "microseconds": datetime.strftime(self.data[source.time_field], "%f"),
        }

    @property
    def as_json(self):
        return json.dumps(self.as_dict(), default=str)

    def as_dict(self):
        data = {}
        for name, source_field in self.source._fields.items():
            if source_field["type"] == "jsonstring":
                value = json.loads(self.data[name])
            else:
                value = self.data[name]
            data[name] = value
        return {"time": self.time, "data": data}
