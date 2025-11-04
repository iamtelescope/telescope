from django.db import migrations


def migrate_connections_forward(apps, schema_editor):
    """
    For each existing source:
    1. Create a Connection from source connection data
    2. Link the connection to the source via source.conn
    3. Replicate RBAC bindings from source to connection
    """
    Source = apps.get_model("telescope", "Source")
    Connection = apps.get_model("telescope", "Connection")
    SourceRoleBinding = apps.get_model("telescope", "SourceRoleBinding")
    ConnectionRoleBinding = apps.get_model("telescope", "ConnectionRoleBinding")

    # Role names that exist for both Source and Connection
    SHARED_ROLES = ["owner", "editor", "viewer", "user"]

    for source in Source.objects.all():
        # Extract connection data based on kind
        connection_data = dict(source.connection) if source.connection else {}

        if source.kind == "clickhouse":
            # For ClickHouse, move database/table to source.data
            database = connection_data.pop("database", None)
            table = connection_data.pop("table", None)

            # Initialize source.data if it doesn't exist
            if not source.data:
                source.data = {}

            # Add database/table to source.data
            if database:
                source.data["database"] = database
            if table:
                source.data["table"] = table

        # Create Connection object
        connection = Connection.objects.create(
            kind=source.kind,
            name=source.name,
            description=f'automatically created from source "{source.slug}" during migration',
            data=connection_data,
        )

        # Link connection to source
        source.conn = connection
        source.save()

        # Replicate RBAC bindings from source to connection
        source_bindings = SourceRoleBinding.objects.filter(source=source)

        for binding in source_bindings:
            # Only replicate roles that exist for both Source and Connection
            if binding.role in SHARED_ROLES:
                ConnectionRoleBinding.objects.create(
                    connection=connection,
                    user=binding.user,
                    group=binding.group,
                    role=binding.role,
                )


class Migration(migrations.Migration):

    dependencies = [
        ("telescope", "0010_connections"),
    ]

    operations = [
        migrations.RunPython(migrate_connections_forward),
    ]
