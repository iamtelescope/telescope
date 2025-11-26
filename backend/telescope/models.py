import logging
import secrets
from typing import List, Dict

from django.db import models
from django.contrib.auth.models import User, Group

from telescope.constants import VIEW_SCOPE_SOURCE, VIEW_SCOPE_PERSONAL

logger = logging.getLogger("telescope.models")


class SourceField:
    def __init__(
        self,
        name: str,
        display_name: str,
        type: str,
        jsonstring: bool,
        autocomplete: bool,
        suggest: bool,
        group_by: bool,
        values: List[str],
    ):
        self.name = name
        self.display_name = display_name
        self.type = type
        self.jsonstring = jsonstring
        self.autocomplete = autocomplete
        self.suggest = suggest
        self.group_by = group_by
        self.values = values


class Connection(models.Model):
    kind = models.CharField(max_length=32)
    name = models.CharField(max_length=64)
    description = models.TextField(blank=True)
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    def __init__(self, *args, **kwargs):
        super(Connection, self).__init__(*args, **kwargs)
        self.permissions = set()

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)

    def add_perms(self, perms):
        for perm in perms:
            self.permissions.add(perm)


class Source(models.Model):
    kind = models.CharField(max_length=32)
    slug = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=64)
    description = models.TextField()
    time_field = models.CharField(max_length=128)
    date_field = models.CharField(max_length=128)
    uniq_field = models.CharField(max_length=128)
    severity_field = models.CharField(max_length=128)
    fields = models.JSONField()
    modifiers = models.JSONField()
    default_chosen_fields = models.JSONField()
    support_raw_query = models.BooleanField()
    execute_query_on_open = models.BooleanField(default=True)
    context_fields = models.JSONField()
    conn = models.ForeignKey(Connection, on_delete=models.SET_NULL, null=True)
    data = models.JSONField(default=dict, blank=True)

    def __init__(self, *args, **kwargs):
        super(Source, self).__init__(*args, **kwargs)
        self.permissions = set()

    def __str__(self):
        return self.slug

    def __repr__(self):
        return str(self)

    @classmethod
    def create(cls, kind, data):
        data["context_fields"] = {}
        data["support_raw_query"] = True
        if kind == "docker":
            data["support_raw_query"] = False
            data["context_fields"] = {
                "container": {},
            }
        return Source.objects.create(kind=kind, **data, modifiers=[])

    @property
    def _record_pseudo_id_field(self):
        return "_____record_pseudo_id"

    @property
    def _fields(self) -> Dict[str, SourceField]:
        fields = {}
        for key, value in self.fields.items():
            fields[key] = SourceField(
                name=key,
                display_name=value["display_name"],
                type=value["type"],
                jsonstring=value["jsonstring"],
                autocomplete=value["autocomplete"],
                suggest=value["suggest"],
                group_by=value["group_by"],
                values=value["values"],
            )
        return fields

    def add_perms(self, perms):
        for perm in perms:
            self.permissions.add(perm)


class SavedView(models.Model):
    slug = models.CharField(max_length=262, blank=True)
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=4096)
    source = models.ForeignKey(
        Source,
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    scope = models.CharField(
        max_length=8,
        choices=[
            (VIEW_SCOPE_PERSONAL, VIEW_SCOPE_PERSONAL),
            (VIEW_SCOPE_SOURCE, VIEW_SCOPE_SOURCE),
        ],
        default=VIEW_SCOPE_PERSONAL,
    )
    shared = models.BooleanField(default=False)
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="updater"
    )
    version = models.PositiveIntegerField(default=1)

    def __init__(self, *args, **kwargs):
        super(SavedView, self).__init__(*args, **kwargs)
        self.permissions = set()
        self.kind = ""

    class Meta:
        unique_together = ("source", "slug", "user")

    def is_personal_scope(self):
        return self.scope == VIEW_SCOPE_PERSONAL

    def is_source_scope(self):
        return self.scope == VIEW_SCOPE_SOURCE

    def __str__(self):
        return f"{self.source_id}-{self.slug}"

    def __repr__(self):
        return str(self)

    def add_perms(self, perms):
        for perm in perms:
            self.permissions.add(perm)

    def set_kind(self, kind):
        self.kind = kind


class SourceRoleBinding(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, null=True)
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    role = models.CharField(max_length=32)


class ConnectionRoleBinding(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, null=True)
    connection = models.ForeignKey(Connection, on_delete=models.CASCADE)
    role = models.CharField(max_length=32)


class GlobalRoleBinding(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, null=True)
    role = models.CharField(max_length=32)


class APIToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=40, unique=True, db_index=True)
    created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=64)

    @classmethod
    def create(cls, user, name):
        return APIToken.objects.create(
            name=name,
            user=user,
            token=secrets.token_hex(20),
        )
