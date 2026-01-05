# Data migration to update SavedView JSON data from "fields" to "columns"

from django.db import migrations


def migrate_savedview_data(apps, schema_editor):
    """
    Update all SavedView data JSON fields to use new column terminology:
    - fields -> columns
    - context_fields -> context_columns
    """
    SavedView = apps.get_model("telescope", "SavedView")

    for view in SavedView.objects.all():
        updated = False

        # Rename 'fields' to 'columns' if it exists
        if "fields" in view.data:
            view.data["columns"] = view.data.pop("fields")
            updated = True

        # Rename 'context_fields' to 'context_columns' if it exists
        if "context_fields" in view.data:
            view.data["context_columns"] = view.data.pop("context_fields")
            updated = True

        if updated:
            view.save()


def reverse_migrate_savedview_data(apps, schema_editor):
    """
    Reverse migration: restore old field names
    """
    SavedView = apps.get_model("telescope", "SavedView")

    for view in SavedView.objects.all():
        updated = False

        # Rename 'columns' back to 'fields' if it exists
        if "columns" in view.data:
            view.data["fields"] = view.data.pop("columns")
            updated = True

        # Rename 'context_columns' back to 'context_fields' if it exists
        if "context_columns" in view.data:
            view.data["context_fields"] = view.data.pop("context_columns")
            updated = True

        if updated:
            view.save()


class Migration(migrations.Migration):

    dependencies = [
        ("telescope", "0016_rename_fields_to_columns"),
    ]

    operations = [
        migrations.RunPython(migrate_savedview_data, reverse_migrate_savedview_data),
    ]
