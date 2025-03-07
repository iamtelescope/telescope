import logging

from django.db import models
from django.contrib.auth.models import User, Group


logger = logging.getLogger("telescope.models")


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
    connection = models.JSONField()

    def __init__(self, *args, **kwargs):
        super(Source, self).__init__(*args, **kwargs)
        self.permissions = set()

    @classmethod
    def create(self, data, username):
        return Source.objects.create(**data, modifiers=[])

    @property
    def _record_pseudo_id_field(self):
        return "_____record_pseudo_id"

    @property
    def _fields(self):
        fields = {}
        for key, value in self.fields.items():
            fields[key] = {
                "name": key,
                "type": value["type"],
                "jsonstring": value["jsonstring"],
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
