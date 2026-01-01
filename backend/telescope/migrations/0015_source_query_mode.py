from django.db import migrations, models


def set_initial_query_mode(apps, schema_editor):
    Source = apps.get_model("telescope", "Source")

    Source.objects.filter(kind="kubernetes").update(query_mode="combined")
    Source.objects.filter(kind="docker").update(query_mode="combined")


class Migration(migrations.Migration):

    dependencies = [
        ("telescope", "0014_source_execute_query_on_open"),
    ]

    operations = [
        migrations.AddField(
            model_name="source",
            name="query_mode",
            field=models.CharField(default="separate", max_length=16),
        ),
        migrations.RunPython(set_initial_query_mode, migrations.RunPython.noop),
    ]
