from django.db import migrations, transaction


def migrate_source_fields(apps, schema_editor):
    if schema_editor.connection.alias != "default":
        return

    model = apps.get_model("telescope", "Source")

    with transaction.atomic():
        for source in model.objects.filter(kind="clickhouse"):
            ca_certs = source.connection.get("ca_certs", "")
            try:
                del source.connection["ca_certs"]
            except KeyError:
                pass
            source.connection["ca_cert"] = ca_certs
            source.save()


class Migration(migrations.Migration):
    dependencies = [
        ("telescope", "0008_savedview"),
    ]

    operations = [
        migrations.RunPython(migrate_source_fields),
    ]
