# [Telescope](https://iamtelescope.net/) - web-based log viewer UI
_A handy tool that manages to make close what once was far_

## Introduction

**Telescope** is a web application designed to provide an intuitive interface for exploring log data. It supports multiple types of sources, including [**ClickHouse**](https://github.com/ClickHouse/ClickHouse), [**StarRocks**](https://github.com/StarRocks/starrocks), [**Docker**](https://www.docker.com/), and [**Kubernetes**](https://kubernetes.io/). Users can configure connections to their ClickHouse or StarRocks databases, access container logs via the Docker API, or retrieve pod logs from Kubernetes clusters. Telescope provides a unified querying experience across different source types, allowing users to filter, search, and analyze logs efficiently. While ClickHouse and StarRocks serve as the primary backends for structured log storage, Docker and Kubernetes support offers convenient options for local development, ephemeral environments, or cloud-native deployments. Future versions may further extend source support.


![Source data](screenshots/main.png?raw=true "Source data")

:framed_picture: **[More Screenshots](screenshots/README.md)**

:blue_book: **[Read the Documentation](https://docs.iamtelescope.net/)**

:speech_balloon: **[Telegram](https://t.me/+CGnCz48GF8xmY2Yy)**

:whale:	**[Run locally using Docker](https://docs.iamtelescope.net/#quickstart)**

## 🚀 Live installation
An live instance is available at [https://demo.iamtelescope.net](https://demo.iamtelescope.net).
You can log in via GitHub to explore the core features of the system from an end-user perspective.
> [!NOTE]
> The live version is intended for demonstration purposes and does not showcase administrative features of the system.

## Key Features

### 🔗 Source Management
- Create and manage **multiple connections** to different data sources, including ClickHouse, StarRocks, Docker, and Kubernetes.
- Define which fields from a source should be used, and configure which ones are **suggested**, hidden, or support **autocompletion**.
- Configure which users and groups have access to a source and define their **permissions**.
- Point a ClickHouse source at OpenTelemetry tables and Telescope **detects the column roles** (logs, traces or metrics) and suggests **links** between the logs, traces and metrics sources.

### 📊 Data Explorer

- Gain insights into your logs with dynamic visualizations and interactive graphs.
- Customize your view by selecting relevant columns, adjusting data presentation, and applying filters to focus on what matters most.
- Use a time and date selector with support for relative time ranges to refine your log queries effortlessly.
- Configure **graph grouping**, including support for nested fields like **JSON strings, Maps or Arrays**.
- Execute advanced queries with **RAW SQL filtering** using `WHERE` clause with ClickHouse or StarRocks SQL expressions for precise data filtering.
- Narrow results with the **facets** sidebar: top values per column, include or exclude with a click, and pinned facets kept per user.
- Follow new rows with **live tail**, every 2, 5 or 10 seconds.
- Open any row in the **row panel**: flattened fields, JSON, the surrounding records in **context**, the row's trace and its pod or node metrics.
- Group similar messages into **patterns**, and compare a dragged selection of a **heatmap** against the rest of the data with **event deltas**.
- Export the visible rows as **CSV** or JSON, rerun queries from the **query history**, and keep **saved views** with tags and favorites.
- Enjoy a clean, minimalist design that keeps the focus on your log data, ensuring a seamless and distraction-free analysis experience.

### 🔭 OpenTelemetry
- Open a trace as a **waterfall** with its critical path, span details, a per-trace service map and the linked logs.
- See how services call each other on the **service map**, coloured by error rate, p95 latency or throughput, with sampling for large ranges.
- Chart gauges, counters (`rate`, `increase`) and histogram percentiles in the **metrics explorer**.
- Spot deploys with **release markers** where a service reports a new `service.version`.

### 📈 Dashboards
- Build dashboards from line, area, bar, number, table, top N, pie, heatmap, text, **log rows** and **patterns** tiles, laid out in collapsible **sections**.
- Combine series with formulas, compare with the previous period and format numbers by unit.
- Filter a whole dashboard with **variables** (`$service`, `var-service=` in the URL).
- Query ClickHouse directly in **raw SQL tiles**, available only to users holding the `raw_sql_user` role on the connection.
- Start from **templates** for services, Kubernetes, the ClickHouse system tables and the JVM, Go, Node.js, Python and .NET runtimes.
- Share, favorite, export and import dashboards, show them in **kiosk mode**, and try a chart in the **chart explorer** before saving it.

### 🔔 Alerts
- Alert on a search or on a dashboard tile, with thresholds, ranges, group by and "N of M windows" conditions.
- Notify **Slack**, **PagerDuty**, **email** or any **webhook** with a templated body.
- Silence, disable, test and review each alert's evaluation **history**; a separate **scheduler** process evaluates them.

### 🔌 API and MCP
- Manage dashboards, alerts and saved views and run searches and charts through **API v2** (`/api/v1`) with personal tokens and an OpenAPI description.
- Connect AI assistants through the built-in **MCP server** (`/api/mcp`), which checks the same permissions as the UI.

### ⌨️ Navigation
- Jump to any page, dashboard, saved view or source from the **command palette** (`⌘K` / `Ctrl+K`).
- Press `?` for the **keyboard shortcuts**, and switch between light and dark themes.

### 🔒 Role-Based Access Control (RBAC) and Authentication Support
- Authenticate with GitHub, with the ability to enforce **organization membership** requirements for access control, or with Okta.
- Define and manage **user and group permissions** to control access to specific sources based on their roles.

## Contributing

Patches are welcome! Please take a look at [Contributing guidelines](CONTRIBUTING.md).

## βeta notion

> [!WARNING]
> Telescope is currently in its $${\color{red}βeta}$$ stage, which means:
>
> - Some features may be incomplete or missing.
> - Certain components might not work as expected or could behave inconsistently.
> - Bugs or issues may occur during usage.
> - From a development and operational perspective, the system may not yet offer full convenience or polish.

## Beyond βeta
Features planned for future implementation ([Telescope 1.0.0 milestone](https://github.com/iamtelescope/telescope/milestone/1))

- ~~[Display records in context](https://github.com/iamtelescope/telescope/issues/35).~~
- [Snapshot storage for long-term retention of log records, preventing data loss due to rotation](https://github.com/iamtelescope/telescope/issues/32).
- ~~[Live log trailing](https://github.com/iamtelescope/telescope/issues/31).~~
- ~~Server-side modifiers (e.g., utilizing ClickHouse functions).~~ (I’ve decided that this feature is not required for stable release)
- ~~[Helm chart](https://github.com/iamtelescope/telescope/issues/30).~~
- ~~SAML and other authentication methods support.~~ (I’ve decided that this feature is not required for stable release)
- [Audit log for any changes inside system](https://github.com/iamtelescope/telescope/issues/34).
