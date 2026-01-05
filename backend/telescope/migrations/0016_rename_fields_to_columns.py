# Generated migration for renaming "field" terminology to "column"

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("telescope", "0015_source_query_mode"),
    ]

    operations = [
        migrations.RenameField(
            model_name="source",
            old_name="time_field",
            new_name="time_column",
        ),
        migrations.RenameField(
            model_name="source",
            old_name="date_field",
            new_name="date_column",
        ),
        migrations.RenameField(
            model_name="source",
            old_name="uniq_field",
            new_name="uniq_column",
        ),
        migrations.RenameField(
            model_name="source",
            old_name="severity_field",
            new_name="severity_column",
        ),
        migrations.RenameField(
            model_name="source",
            old_name="fields",
            new_name="columns",
        ),
        migrations.RenameField(
            model_name="source",
            old_name="default_chosen_fields",
            new_name="default_chosen_columns",
        ),
        migrations.RenameField(
            model_name="source",
            old_name="context_fields",
            new_name="context_columns",
        ),
    ]
