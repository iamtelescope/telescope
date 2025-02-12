# Telescope
_A handy tool that manages to make close what once was far_

![telescope](ui/src/assets/logo.png?raw=true)

## Introduction

**Telescope** is a web application designed to facilitate log exploration and analysis for logs stored in **ClickHouse**. It enables users to create and configure **sources** to ClickHouse databases and subsequently use these sources to query logs data.

![Source data](screenshots/main.png?raw=true "Source data")

**[Read the Documentation](https://iamtelescope.github.io/telescope/docs/)**

### Key Features

- **Source management**: Create and manage connections to [ClickHouse](https://github.com/ClickHouse/ClickHouse) databases for log analysis.
- **Logs exploration**: Select which columns to display, customize how data is presented, and apply filters to refine results.
- **Role-Based Access Control (RBAC)**: Define and manage user permissions to control access to specific sources.

> [!CAUTION]
> Telescope is currently in its $${\color{red}βeta}$$ stage, which means:
>
> - Some features may be incomplete or missing.
> - Certain components might not work as expected or could behave inconsistently.
> - Bugs or issues may occur during usage.
> - From a development and operational perspective, the system may not yet offer full convenience or polish.
> - Was not used in production, so it might encounter some performance issues on real installations.

### Live installation
An live instance is available at [https://telescope.humanuser.net](https://telescope.humanuser.net).
You can log in via GitHub to explore the core features of the system from an end-user perspective.
> [!NOTE]
> The live version is intended for demonstration purposes and does not showcase administrative features of the system.

### Beyond βeta
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
