# [Telescope](https://iamtelescope.net/) - web-based log viewer UI
_A handy tool that manages to make close what once was far_

## Introduction

**Telescope** is a web application designed to provide an intuitive interface for exploring log data. It supports multiple types of sources, including [**ClickHouse**](https://github.com/ClickHouse/ClickHouse), [**Docker**](https://www.docker.com/), and [**Kubernetes**](https://kubernetes.io/). Users can configure connections to their ClickHouse databases, access container logs via the Docker API, or retrieve pod logs from Kubernetes clusters. Telescope provides a unified querying experience across different source types, allowing users to filter, search, and analyze logs efficiently. While ClickHouse remains the primary backend for structured log storage, Docker and Kubernetes support offers convenient options for local development, ephemeral environments, or cloud-native deployments. Future versions may further extend source support.


![Source data](screenshots/main.png?raw=true "Source data")

:framed_picture: **[More Screenshots](screenshots/README.md)**

:blue_book: **[Read the Documentation](https://docs.iamtelescope.net/)**

:speech_balloon: **[Telegram](https://t.me/+CGnCz48GF8xmY2Yy)**

:whale:	**[Run locally using Docker](https://iamtelescope.github.io/telescope/docs/setup/quickstart.html)**

## 🚀 Live installation
An live instance is available at [https://demo.iamtelescope.net](https://demo.iamtelescope.net).
You can log in via GitHub to explore the core features of the system from an end-user perspective.
> [!NOTE]
> The live version is intended for demonstration purposes and does not showcase administrative features of the system.

## Key Features

### 🔗 Source Management
- Create and manage **multiple connections** to different data sources, including ClickHouse, Docker, and Kubernetes.
- Define which fields from a source should be used, and configure which ones are **suggested**, hidden, or support **autocompletion**.
- Configure which users and groups have access to a source and define their **permissions**.

### 📊 Data Explorer

- Gain insights into your logs with dynamic visualizations and interactive graphs.
- Customize your view by selecting relevant columns, adjusting data presentation, and applying filters to focus on what matters most.
- Use a time and date selector with support for relative time ranges to refine your log queries effortlessly.
- Configure **graph grouping**, including support for nested fields like **JSON strings, Maps or Arrays**.
- Execute advanced queries with **RAW SQL filtering** using `WHERE` clause with ClickHouse SQL expressions for precise data filtering.
- Enjoy a clean, minimalist design that keeps the focus on your log data, ensuring a seamless and distraction-free analysis experience.

### 🔒 Role-Based Access Control (RBAC) and Authentication Support
- Authenticate with GitHub, with the ability to enforce **organization membership** requirements for access control.
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

- [Display records in context](https://github.com/iamtelescope/telescope/issues/35).
- [Snapshot storage for long-term retention of log records, preventing data loss due to rotation](https://github.com/iamtelescope/telescope/issues/32).
- [Live log trailing](https://github.com/iamtelescope/telescope/issues/31).
- ~~Server-side modifiers (e.g., utilizing ClickHouse functions).~~ (I’ve decided that this feature is not required for stable release)
- [Helm chart](https://github.com/iamtelescope/telescope/issues/30).
- ~~SAML and other authentication methods support.~~ (I’ve decided that this feature is not required for stable release)
- [Audit log for any changes inside system](https://github.com/iamtelescope/telescope/issues/34).
