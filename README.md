# Telescope
_A handy tool that manages to make close what once was far_

## Introduction

**Telescope** is a web application designed to provide an intuitive interface for exploring log data. It is built to work with any type of logs, as long as they are stored in [**ClickHouse**](https://github.com/ClickHouse/ClickHouse). Users can easily configure connections to their ClickHouse databases and run queries to filter, search, and analyze logs efficiently. While ClickHouse is the primary supported storage backend, future versions of Telescope may introduce support for additional data sources.

![Source data](screenshots/main.png?raw=true "Source data")

:framed_picture: **[More Screenshots](screenshots/README.md)**

:blue_book: **[Read the Documentation](https://iamtelescope.github.io/telescope/docs/)**

:speech_balloon: **[Discord](https://discord.gg/rXpjDnEc)**

## 🚀 Live installation
An live instance is available at [https://telescope.humanuser.net](https://telescope.humanuser.net).
You can log in via GitHub to explore the core features of the system from an end-user perspective.
> [!NOTE]
> The live version is intended for demonstration purposes and does not showcase administrative features of the system.

## Key Features

### 🔗 Source Management
- 🖥️ Create and manage multiple connections to different ClickHouse clusters.
- 📑 Choose which fields of a table to use and configure which should be suggested, hidden, or support autocompletion.
- 🔐 Configure which users and groups have access to a source and define their permissions.

### 📊 Data Explorer
- 📈 Gain insights into your logs with dynamic visualizations and interactive graphs.
- 🛠️ Customize your view by selecting relevant columns, adjusting data presentation, and applying filters to focus on what matters most.
- ⏳ Use a time and date selector with support for relative time ranges to refine your log queries effortlessly.
- 🎨 Enjoy a clean, minimalist design that keeps the focus on your log data, ensuring a seamless and distraction-free analysis experience.

### 🔒 Role-Based Access Control (RBAC) and Authentication Support
- 🔑 Authenticate with GitHub, with the ability to enforce organization membership requirements for access control.
- 👥 Define and manage user and group permissions to control access to specific sources based on their roles.


## βeta notion

> [!CAUTION]
> Telescope is currently in its $${\color{red}βeta}$$ stage, which means:
>
> - Some features may be incomplete or missing.
> - Certain components might not work as expected or could behave inconsistently.
> - Bugs or issues may occur during usage.
> - From a development and operational perspective, the system may not yet offer full convenience or polish.
> - Was not used in production, so it might encounter some performance issues on real installations.

## Beyond βeta
Features planned for future implementation:

- Ability to store fields and query presets for easier log searches.
- Grant expert users the ability to write raw SQL `WHERE` statements.
- Support custom `GROUP BY` columns for graphs. 
- Display records in context.
- Snapshot storage for long-term retention of log records, preventing data loss due to rotation.
- Live log trailing.
- Server-side modifiers (e.g., utilizing ClickHouse functions).
- Time zone support for the datetime selector.
- Helm chart.
- SAML and other authentication methods support.
- Audit log for any changes inside system.
