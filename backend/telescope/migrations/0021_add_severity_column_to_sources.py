from django.db import migrations


def add_severity_column(apps, schema_editor):
    """
    Add 'severity' column to Docker and Kubernetes sources.
    """
    Source = apps.get_model("telescope", "Source")

    severity_column_config = {
        "display_name": "",
        "type": "string",
        "autocomplete": False,
        "suggest": True,
        "jsonstring": False,
        "group_by": True,
        "values": [],
    }

    for source in Source.objects.filter(kind__in=["docker", "kubernetes"]):
        if "severity" not in source.columns:
            source.columns["severity"] = severity_column_config
            source.save()


def remove_severity_column(apps, schema_editor):
    """
    Remove 'severity' column from Docker and Kubernetes sources.
    """
    Source = apps.get_model("telescope", "Source")

    for source in Source.objects.filter(kind__in=["docker", "kubernetes"]):
        if "severity" in source.columns:
            del source.columns["severity"]
            source.save()


class Migration(migrations.Migration):
    dependencies = [
        ("telescope", "0020_set_default_severity_column"),
    ]

    operations = [
        migrations.RunPython(add_severity_column, remove_severity_column),
    ]
