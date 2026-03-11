from django.db import migrations, models


def seed_healthcheck(apps, schema_editor):
    HealthCheck = apps.get_model("telescope", "HealthCheck")
    HealthCheck.objects.create(key="status", value="ok")


def remove_healthcheck(apps, schema_editor):
    HealthCheck = apps.get_model("telescope", "HealthCheck")
    HealthCheck.objects.filter(key="status").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("telescope", "0021_add_severity_column_to_sources"),
    ]

    operations = [
        migrations.CreateModel(
            name="HealthCheck",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("key", models.CharField(max_length=64, unique=True)),
                ("value", models.CharField(max_length=256)),
            ],
        ),
        migrations.RunPython(seed_healthcheck, remove_healthcheck),
    ]
