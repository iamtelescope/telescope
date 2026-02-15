from django.db import migrations


def rename_message_to_body(apps, schema_editor):
    Source = apps.get_model("telescope", "Source")

    for source in Source.objects.filter(kind__in=["docker", "kubernetes"]):
        updated = False

        if "message" in source.columns:
            source.columns["body"] = source.columns.pop("message")
            updated = True

        if isinstance(source.default_chosen_columns, list):
            if "message" in source.default_chosen_columns:
                idx = source.default_chosen_columns.index("message")
                source.default_chosen_columns[idx] = "body"
                updated = True

        if updated:
            source.save()


def reverse_rename(apps, schema_editor):
    Source = apps.get_model("telescope", "Source")

    for source in Source.objects.filter(kind__in=["docker", "kubernetes"]):
        updated = False

        if "body" in source.columns:
            source.columns["message"] = source.columns.pop("body")
            updated = True

        if isinstance(source.default_chosen_columns, list):
            if "body" in source.default_chosen_columns:
                idx = source.default_chosen_columns.index("body")
                source.default_chosen_columns[idx] = "message"
                updated = True

        if updated:
            source.save()


class Migration(migrations.Migration):
    dependencies = [
        ("telescope", "0018_source_severity_rules"),
    ]

    operations = [
        migrations.RunPython(rename_message_to_body, reverse_rename),
    ]
