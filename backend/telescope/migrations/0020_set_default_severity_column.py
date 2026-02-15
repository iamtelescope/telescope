from django.db import migrations


def set_severity_column(apps, schema_editor):
    Source = apps.get_model("telescope", "Source")

    for source in Source.objects.filter(kind__in=["docker", "kubernetes"]):
        if not source.severity_column or source.severity_column == "":
            source.severity_column = "severity"
            source.save()


def reverse_set_severity_column(apps, schema_editor):
    Source = apps.get_model("telescope", "Source")

    for source in Source.objects.filter(kind__in=["docker", "kubernetes"]):
        if source.severity_column == "severity":
            source.severity_column = ""
            source.save()


class Migration(migrations.Migration):
    dependencies = [
        ("telescope", "0019_rename_message_to_body"),
    ]

    operations = [
        migrations.RunPython(set_severity_column, reverse_set_severity_column),
    ]
