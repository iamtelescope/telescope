# Fields Input

The Fields Input allows you to precisely define which fields appear in the resulting table and how they are formatted. Each field definition is a comma-separated entry that must correspond to a field in the source; otherwise, an error will occur.

Use the Fields Input to control exactly which data appears in your output table and how it is displayed.

## Field Definition Format

Each field definition can include the following components:

1. **Field Name** - The base name of the field you wish to display.

2. **Modifiers (Optional)** - Use modifiers to transform or format the field's data. Append a modifier using the `|` symbol. Multiple modifiers can be chained together, and they are applied sequentially. Multiple arguments can be passed with comma-separated manner.

   **Example:**
   - `message|chars(25)` – Applies the `chars(25)` modifier to limit the text length.
   - `message|lastline|chars(25)` – Extracts the last line of the message and then limits it to 25 characters.
   - `message|split(\t)|slice(-1)|join|format(json)|highlight(json)` - Splits the message into an array using a tab (`\t`) as the delimiter, extracts the last element, joins it back into a string, formats it as JSON, and applies JSON syntax highlighting. This can be useful when `message` contains a tab-separated log where one of the parts is a valid JSON that needs to be examined in detail (e.g., logs of requests and their parameters sent by an application).

    Currently, **only client-side modifiers** are supported. You can check the exact code of the modifiers [here](https://github.com/iamtelescope/telescope/blob/main/ui/src/utils/modifiers.js)

3. **Alias (Optional)** - Assign an alias to rename the field in the output. If an alias is desired, it should be added after all modifiers using the `as` keyword.

   **Example:**
   - `message as msg`
   - `message|lastline|chars(25) as message`


## Working with JSON, Map, and Array Fields  

For fields stored as JSON strings, Maps, or Arrays, you can extract nested values using a colon (`:`) as a delimiter.

### JSON Fields  
You can navigate JSON structures using the field path separated by colons.

**Example:**  
```plaintext
rest:app:request:bytes
```
For the JSON object:
```json
{
  "rest": {
    "app": {
      "request": {
        "bytes": 25
      }
    }
  }
}
```
This expression returns `25`. If the specified key does not exist, an empty string is returned.  

### Map Fields  
For **Map**-type fields, you can access values using the key name.

**Example:**  
```plaintext
metadata:request_id
```
For the map:
```json
{
  "metadata": {
    "request_id": "abc-123"
  }
}
```
This expression returns `"abc-123"`.  

### Array Fields  
For **Array**-type fields, you can access elements by index.

**Example:**  
```plaintext
errors:0
```
For the array:
```json
{
  "errors": ["Error A", "Error B", "Error C"]
}
```
This expression returns `"Error A"`.  

Currently, only **one level of nesting** is supported for Maps and Arrays.  

Modifiers can also be applied to extracted values for additional processing.

## Available Modifiers

The following modifiers are currently supported:

### chars
Extracts a substring from the given value based on the specified range. Usage: `chars(from[,to])`, where `from` is the starting index, and `to` (optional) is the ending index. If `to` is not provided, it extracts the first `from` characters.

Example:
`message|chars(5,10)` extracts characters from index 5 to 10.
`message|chars(5)` extracts the first 5 characters.

### lines
Extracts specific lines from the given value based on the specified range. Usage: `lines(from[,to])`, where `from` is the starting line index, and `to` (optional) is the ending line index. If `to` is not provided, it extracts the first `from` lines.

Example:
`message|lines(2,5)` extracts lines from index 2 to 5.
`message|lines(3)` extracts the first 3 lines.

### slice
Extracts a substring from the given value based on the specified range. Usage: `slice(from[,to])`, where `from` is the starting index, and `to` (optional) is the ending index. If `to` is not provided, it extracts from `from` to the end.  

Example:
`message|slice(5,10)` extracts characters from index 5 to 10.
`message|slice(5)` extracts from index 5 to the end.

### firstline
Extracts the first line of text. Usage: `firstline`.

Example:
`message|firstline` extracts the first line from the text.

### lastline
Extracts the last line of text. Usage: `lastline`.

Example:
`message|lastline` extracts the last line from the text.

### oneline
Removes all line breaks from the text, converting it into a single line. Usage: `oneline`.

Example:
`message|oneline` removes all newline characters, making the text a single continuous line.

### lower
Converts all characters in the text to lowercase. Usage: `lower`.

Example:
`message|lower` converts the text to lowercase.

### upper
Converts all characters in the text to uppercase. Usage: `upper`.

Example:
`message|upper` converts the text to uppercase.

### split
Splits the text into an array using the specified delimiter. Usage: `split(splitter)`, where `splitter` is the character or string used to split the text.

Example:
`message|split(",")` splits the text by commas.
`message|split(\t)` splits the text by tab character.

### join
Joins an array into a string using the specified delimiter. Usage: `join(joiner)`, where `joiner` is the character or string used to concatenate the elements.

Example:
`message|join(", ")` joins array elements with a comma and space.

### json
Parses the text as JSON and returns the corresponding object. Usage: `json()`.

Example:
`message|json()` converts a JSON string into an object.

### href
Generates an HTML `<a>` tag by inserting a given value into a URL template. Usage: `|href(urlTemplate, [urlValue])`, where `urlTemplate` is the URL format with `${value}`, and `urlValue` (optional) is the displayed text.

Example: `message|href("https://example.com/item/${value}", "View Item")` produces `<a href="https://example.com/item/12345">View Item</a>`

### format
Alias: `fmt`

Formats a given value based on the specified or detected language. Usage: `|fmt([language])`, where language (optional) is the formatting type ("sql" or "json"). If language is not provided, it is detected automatically.

Example: `message|fmt("json")` produces a formatted JSON string, while `message|fmt("sql")` returns a formatted SQL query.

### highlight
Alias: `hl`

Applies syntax highlighting (via highlight.js lib) for a given value based on the specified or detected language. Usage: `highlight([language])`, where `language` (optional) is `"sql"` or `"json"`. If not provided, it is detected automatically.

Example: `message|highlight("sql")` for SQL queries or `message|highlight("json")` for JSON formatting.


## Summary

- **Comma-Separated Definitions:** Specify multiple fields by separating them with commas.
- **Validation:** Each field must exist in the source; otherwise, an error is raised.
- **Modifiers:** Enhance or transform field data for customized display.
- **Alias:** Optionally rename fields for clarity in the results.
- **JSON Extraction:** Use colon-separated paths to retrieve nested data from JSON strings.
