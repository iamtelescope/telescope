import secrets
import logging
from typing import List, Dict

from django.db import models
from django.contrib.auth.models import User, Group


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
    support_raw_query = models.BooleanField()
    context_fields = models.JSONField()
    connection = models.JSONField()

    def __init__(self, *args, **kwargs):
        super(Source, self).__init__(*args, **kwargs)
        self.permissions = set()

    @classmethod
    def create(self, kind, data, username):
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


class SourceRoleBinding(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, null=True)
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
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
    def create(self, user, name):
        return APIToken.objects.create(
            name=name,
            user=user,
            token=secrets.token_hex(20),
        )
