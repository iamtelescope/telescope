from django.db import migrations, models
from telescope.constants import (
    SOURCE_KIND_DOCKER,
    SOURCE_KIND_KUBERNETES,
    SOURCE_QUERY_MODE_COMBINED,
    SOURCE_QUERY_MODE_SEPARATE,
)


def set_initial_query_mode(apps, schema_editor):
    Source = apps.get_model("telescope", "Source")

    Source.objects.filter(kind=SOURCE_KIND_KUBERNETES).update(
        query_mode=SOURCE_QUERY_MODE_COMBINED
    )
    Source.objects.filter(kind=SOURCE_KIND_DOCKER).update(
        query_mode=SOURCE_QUERY_MODE_COMBINED
    )


class Migration(migrations.Migration):

    dependencies = [
        ("telescope", "0014_source_execute_query_on_open"),
    ]

    operations = [
        migrations.AddField(
            model_name="source",
            name="query_mode",
            field=models.CharField(default=SOURCE_QUERY_MODE_SEPARATE, max_length=16),
        ),
        migrations.RunPython(set_initial_query_mode, migrations.RunPython.noop),
    ]
