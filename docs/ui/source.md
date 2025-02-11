## Create

To create a source, you need to fill in the form data.

### Connection Data
- **`host`** – ClickHouse server host. Defaults to `localhost`.
- **`port`** – ClickHouse server native protocol port. Defaults to `9000`.
- **`user`** – Username used to connect to the server. Defaults to `default`.
- **`password`** – Password used to connect to the server.
- **`database`** – Database name.
- **`table`** – Table name.
- **`ssl`** – Whether to use a secure connection. (Custom SSL certificates are not yet supported.)

After filling in the connection data, you need to test the connection by clicking the **"Validate connection & load schema"** button.

If the connection test is successful, you will later have the option to automatically populate the form fields using the **"Load fields from schema"** button.

If the connection test fails, you can still create the source, but you will need to add the fields manually.

### Common Data
- **`slug`** – A unique [slug](https://docs.djangoproject.com/en/5.1/ref/forms/fields/#slugfield) field. Cannot be changed after creation (used as a human-readable source identifier).
- **`name`** – Source name.
- **`description`** – Source description.

### Fields Setup

In this section, you need to define the list of fields and configure their usage.
If the connection test was previously successful, you can automatically add fields from the retrieved schema using the **"Load fields from schema"** button.

After adding fields, the **"Time field"** and **"Severity field"** options will become selectable from a dropdown list.

- **`Time field`** – Used in the time range selector for querying data.
- **`Severity field`** – Used to apply different colors to messages/graph bars based on severity.
- **`Default chosen fields`** – Comma-separated list of values for the fields selector. Each value in lis shoud exist in fields names list

#### **Field Properties**
Each field has several properties:

- **`Name`** – This name is mapped to the field name in the database table.
- **`Display Name`** – This name is used in the table as alias when querying logs.
- **`Type`** – The field type (Telescope uses its own types to simplify log handling, ensure consistency in the UI, and separate display logic from ClickHouse. In some cases, they match ClickHouse types, while in others, they do not). Only fields with type `datetime` or `datetime64` are visible in `Time field` selector.
- **`Autocomplete`** – A boolean property that defines whether this field should use autocompletion in the query input.
- **`Suggest`** – A boolean property that defines whether this field should be suggested in the query input.
- **`Values`** – A comma-separated list of field values. Used only for the `enum` type.
