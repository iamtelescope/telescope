# Source

A source is an object that defines how to connect to a ClickHouse instance (host, database, username, etc.) and specifies which fields of specified table should be used and how.
Additionally, a source serves as an RBAC instance for binding roles to user and groups.

The Python library [clickhouse-driver](https://clickhouse-driver.readthedocs.io/en/latest/) is used for connecting to ClickHouse and executing queries.
