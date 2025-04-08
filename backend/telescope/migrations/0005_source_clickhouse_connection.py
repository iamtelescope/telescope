from django.db import migrations, transaction

from telescope.models import Source


def migrate_source_fields(apps, schema_editor):
    if schema_editor.connection.alias != "default":
        return

    Source = apps.get_model("telescope", "Source")

    with transaction.atomic():
        for source in Source.objects.filter(kind="clickhouse"):
            source.connection["verify"] = True
            source.connection["ca_certs"] = ""
            source.connection["certfile"] = ""
            source.connection["keyfile"] = ""
            source.connection["ssl_version"] = ""
            source.connection["ciphers"] = ""
            source.connection["server_hostname"] = ""
            source.connection["alt_hosts"] = ""
            source.save()


class Migration(migrations.Migration):
    dependencies = [
        ("telescope", "0004_source_support_raw_query"),
    ]

    operations = [
        migrations.RunPython(migrate_source_fields),
    ]
