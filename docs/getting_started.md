# Running locally

## Prerequisites

- Install [Docker](https://www.docker.com/get-started) on your machine.

## 1. Download the Docker Image

Pull the latest Docker image from GitHub Container Registry:

```sh
docker pull ghcr.io/iamtelescope/telescope:latest
```

## 2. Copy the SQLite Database and config templates

Download the SQLite database template and config template from the repository and save it to a local folder. You can use `wget` to fetch it:

```sh
mkdir ~/.telescope/
wget -O ~/.telescope/db.sqlite3 "https://raw.githubusercontent.com/iamtelescope/telescope/refs/heads/main/dev/db.sqlite3"
wget -O ~/.telescope/config.yaml "https://raw.githubusercontent.com/iamtelescope/telescope/refs/heads/main/dev/config.yaml"
```

## 3. Start the Docker Container

Run the Docker container with the appropriate parameters:

```sh
docker run \
    -e TELESCOPE_CONFIG_FILE="/config.yaml" \
    -v $(realpath ~/.telescope/config.yaml):/config.yaml \
    -v $(realpath ~/.telescope/db.sqlite3):/db.sqlite3 \
    --network host \
    ghcr.io/iamtelescope/telescope:latest
```

Once started, the service will be available on localhost port `9898`.
Proceed to http://localhost:9898/setup to create a superuser account.

## 4. Demo logs

Although setting up and configuring ClickHouse is beyond the scope of this document, the following configuration can be suggested for demo logs.

### 4.1 Prepare database & table

```sql
CREATE DATABASE logs.logs;
CREATE TABLE logs.logs
(
    `timestamp` DateTime64(9, 'UTC') CODEC(Delta(8), ZSTD(1)),
    `host` String CODEC(ZSTD(7)),
    `service` String CODEC(ZSTD(7)),
    `message` String CODEC(ZSTD(7)),
    `source_type` String CODEC(ZSTD(7)),
    `level` Enum8('UNKNOWN' = 0, 'FATAL' = 1, 'ERROR' = 2, 'WARN' = 3, 'INFO' = 4, 'DEBUG' = 5, 'TRACE' = 6),
    `rest` String CODEC(ZSTD(7))
)
ENGINE = MergeTree
PARTITION BY toStartOfHour(timestamp)
PRIMARY KEY (service, timestamp)
ORDER BY (service, timestamp)
TTL toDateTime(timestamp) + toIntervalWeek(1)
SETTINGS index_granularity = 1024;
```

### 4.2 Configure Vector to provide demo logs

https://vector.dev/docs/setup/quickstart/

```yaml
api:
  enabled: true
sources:
  access:
    type: demo_logs
    format: json
    interval: 1
transforms:
  prepare_level:
    type: remap
    inputs:
      - access
    source: |
      .service = "web-server"
      .level = "UNKNOWN"
      .rest = parse_json!(.message)
      .message, _ = "[" + .rest.datetime + "] " + .rest.host + " " + .rest.method + " " + .rest.request + " " + .rest.referer
      code = parse_int!(.rest.status)
      if code < 200 {
        .level = "TRACE"
      } else if code >= 200 && code < 300 {
        .level = "DEBUG"
      } else if code >= 300 && code < 400 {
        .level = "INFO"
      } else if code >= 400  && code < 500 {
        .level = "WARN"
      } else {
        .level = "ERROR"
      }
      .rest.status = code
  prepare_timestamp:
    type: remap
    inputs:
      - prepare_level
    source: |
      .timestamp = format_timestamp!(.timestamp, "%s%f")

sinks:
  clickhouse:
    type: clickhouse
    endpoint: http://localhost:8123
    database: logs
    table: logs
    auth:
      strategy: basic
      user: default
      password: ""
    inputs:
      - prepare_timestamp
    encoding:
      timestamp_format: rfc3339
```
