from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("telescope", "0021_add_severity_column_to_sources"),
    ]

    operations = [
        migrations.AddField(
            model_name="source",
            name="order_by_expression",
            field=models.CharField(blank=True, default="", max_length=512),
        ),
    ]
