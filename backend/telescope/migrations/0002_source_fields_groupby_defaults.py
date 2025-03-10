from django.db import migrations, transaction

from telescope.models import Source


def migrate_source_fields(apps, schema_editor):
    if schema_editor.connection.alias != "default":
        return

    with transaction.atomic():
        for source in Source.objects.all():
            for key, value in source.fields.items():
                if 'group_by' not in value:
                    value['group_by'] = False
            source.save()


class Migration(migrations.Migration):
    dependencies = [
        ("telescope",  "0001_initial"),
    ]

    operations = [
        migrations.RunPython(migrate_source_fields),
    ]
