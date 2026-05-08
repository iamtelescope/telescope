import logging

from django.db import migrations, models

logger = logging.getLogger("telescope.migrations.0023")

TRANSFORMER_NAMES = {
    "chars",
    "lines",
    "firstline",
    "lastline",
    "oneline",
    "lower",
    "upper",
    "slice",
    "split",
    "join",
    "json",
    "str",
    "type",
    "fmt",
    "format",
}

RENDERER_NAMES = {"highlight", "hl", "href"}


def split_modifiers_forward(apps, schema_editor):
    Source = apps.get_model("telescope", "Source")
    for source in Source.objects.all():
        legacy = source.modifiers
        if not isinstance(legacy, list):
            legacy = []
        transformers = []
        renderers = []
        for item in legacy:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if name in RENDERER_NAMES:
                renderers.append(item)
            elif name in TRANSFORMER_NAMES:
                transformers.append(item)
            else:
                logger.warning(
                    "source %r: dropping unknown modifier %r during 0023 split",
                    source.slug,
                    name,
                )
        source.transformers = transformers
        source.renderers = renderers
        source.save(update_fields=["transformers", "renderers"])


class Migration(migrations.Migration):

    dependencies = [
        ("telescope", "0022_healthcheck"),
    ]

    operations = [
        migrations.AddField(
            model_name="source",
            name="transformers",
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name="source",
            name="renderers",
            field=models.JSONField(default=list),
        ),
        migrations.RunPython(split_modifiers_forward, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="source",
            name="modifiers",
        ),
    ]
