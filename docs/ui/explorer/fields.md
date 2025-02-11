# Fields Input

The Fields Input allows you to precisely define which fields appear in the resulting table and how they are formatted. Each field definition is a comma-separated entry that must correspond to a field in the source; otherwise, an error will occur.

Use the Fields Input to control exactly which data appears in your output table and how it is displayed.

## Field Definition Format

Each field definition can include the following components:

1. **Field Name** - The base name of the field you wish to display.

2. **Modifiers (Optional)** - Use modifiers to transform or format the field's data. Append a modifier using the `|` symbol. Multiple modifiers can be chained together, and they are applied sequentially. Multiple arguments can be passed with comma-separated manner.

   **Example:**
   - `message|chars(25)` – Applies the `chars(25)` modifier to limit the text.
   - `message|lastline|chars(25)` – Extracts the last line of the message and then limits it to 25 characters.

    Currently, **only client-side modifiers** are supported. You can check the exact code of the modifiers [here](https://github.com/iamtelescope/telescope/blob/main/ui/src/utils/modifiers.js)

3. **Alias (Optional)** - Assign an alias to rename the field in the output. If an alias is desired, it should be added after all modifiers using the `as` keyword.

   **Example:**
   - `message as msg`
   - `message|lastline|chars(25) as message`

## Working with JSON Fields

For fields stored as JSON strings, you can extract nested values using a colon (`:`) as a delimiter.
**Example:**
- `rest:app:request:bytes`
  This expression navigates the JSON structure `{ "rest": { "app": { "request": { "bytes": 25 } } } }` and returns the value `25`.
If the specified key does not exist, an empty string is returned. Modifiers can also be applied to values extracted from JSON fields.

## Available Modifiers

The following modifiers are currently supported:

- **chars:** Limits the number of characters.
- **lines:** Limits the number of lines.
- **firstline:** Extracts the first line of text.
- **lastline:** Extracts the last line of text.
- **oneline:** Converts multi-line text into a single line.
- **lower:** Converts text to lowercase.
- **upper:** Converts text to uppercase.
- **slice:** Extracts a substring or sublist.
- **split:** Splits the text based on a delimiter.
- **join:** Joins segments.
- **json:** Parses JSON data.

## Summary

- **Comma-Separated Definitions:** Specify multiple fields by separating them with commas.
- **Validation:** Each field must exist in the source; otherwise, an error is raised.
- **Modifiers:** Enhance or transform field data for customized display.
- **Alias:** Optionally rename fields for clarity in the results.
- **JSON Extraction:** Use colon-separated paths to retrieve nested data from JSON strings.
