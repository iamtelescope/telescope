# Query input

Query input syntax is [FlyQL](https://github.com/iamtelescope/flyql) syntax. Please refer FlyQL doc.

For ClickHouse sources queries generates by [FlyQL ClickHouse generator](https://github.com/iamtelescope/flyql-generators/tree/main/python/flyql_generators)

Despite the fact that the documentation for flyql and flyql ClickHouse generator is located in their respective repositories, a few query examples are provided here to give a basic understanding of how to query data inside Telescope.

`host=localhost` - Selects records where the `host` field is exactly `"localhost"`.

`host!=localhost` - Selects records where the `host` field is **not** `"localhost"`.

`host=l*ohost` - Selects records where the `host` field starts with `"l"`, ends with `"ohost"`, and has any characters in between.

`host=localhost and message=2025*` - Selects records where the `host` is `"localhost"` and the `message` field starts with `"2025"`.

`(host=localhost or host=remote) and not host=puppet` - Selects records where the `host` is either `"localhost"` or `"remote"`, but **not** `"puppet"`.

`rest:bytes>=25` - Selects records where the `bytes` field inside the `rest` JSON object is greater than or equal to `25`.

`rest:url=~".*monkey.*"` - Selects records where the `url` field inside the `rest` JSON object contains the word `"monkey"` anywhere in the string.
