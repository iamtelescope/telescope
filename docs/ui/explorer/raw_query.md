# Raw Query Input

For users with the necessary **permissions**, it is possible to pass **custom SQL `WHERE` expressions** for filtering data.

-   The input must be in **ClickHouse SQL format**.
-   **Do not include** the `WHERE` keyword - only write the condition that follows it.
-   The raw query input is appended to the existing query as:

    ```sql
    WHERE {telescope_generated_clause} AND {raw_query_input_clause}
    ```

## Example Usage (Regex on `message` Field):

To filter logs where the `message` field contains the word **"error"** anywhere in the text, you can use a **regular expression**:

```sql
message ILIKE '%error%'
```

Or, if you need a **more advanced regex match** in ClickHouse, use:

```sql
match(message, '.*error.*')
```

This ensures only messages containing "error" will be included in the results, while still applying any other active filters.
