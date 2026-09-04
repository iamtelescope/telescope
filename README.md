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

### 📊 Data Explorer

- Gain insights into your logs with dynamic visualizations and interactive graphs.
- Customize your view by selecting relevant columns, adjusting data presentation, and applying filters to focus on what matters most.
- Use a time and date selector with support for relative time ranges to refine your log queries effortlessly.
- Configure **graph grouping**, including support for nested fields like **JSON strings, Maps or Arrays**.
- Execute advanced queries with **RAW SQL filtering** using `WHERE` clause with ClickHouse or StarRocks SQL expressions for precise data filtering.
- Enjoy a clean, minimalist design that keeps the focus on your log data, ensuring a seamless and distraction-free analysis experience.

### 🔒 Role-Based Access Control (RBAC) and Authentication Support
- Authenticate with GitHub, with the ability to enforce **organization membership** requirements for access control.
- Define and manage **user and group permissions** to control access to specific sources based on their roles.


### Authentication configuration

Telescope supports browser login with GitHub, Okta, and Keycloak. Keycloak uses
the generic OpenID Connect provider and one configured realm. Set its issuer
URL (not the Keycloak server root) in `server_url`; Telescope discovers the
authorization, token, and userinfo endpoints from that realm's
`/.well-known/openid-configuration`.

Example Keycloak configuration:

```yaml
auth:
  providers:
    keycloak:
      enabled: true
      client_id: "telescope"
      secret: !env KEYCLOAK_SECRET
      server_url: "https://sso.example/realms/telescope"
      default_group: "telescope-users"
  force_auth_provider: keycloak  # optional
```

The Keycloak client must be confidential, have Standard Flow enabled, use
PKCE method `S256`, and allow this redirect URI:

```text
https://<public-host>/login/oidc/keycloak/login/callback/
```

Use an `http://localhost` URI only for local development.

When `frontend.base_url` is configured, include that subpath before
`/login/`. Keycloak groups and roles are not synchronized; a successful login
adds the user only to the configured `default_group`. Logout clears the local
Django session and does not call the Keycloak logout endpoint. REST API
authentication continues to use the existing Session and Telescope API Token
methods.

To place every Keycloak user into a read-only group, set
`default_group` to the exact Telescope group name, for example:

```yaml
default_group: "read only"
```

Create that group in Telescope and assign its `viewer` role on each required
source and connection for configuration-only access. To let users query logs
without edit/delete/grant permissions, assign the `user` role on the required
sources; it grants `source_read` and `source_use`. Use the connection
`viewer` role for connection visibility. Creating sources additionally requires
the global `global_create_source` permission and connection `use` permission.
The group name alone does not grant permissions, and Keycloak group or role
claims are intentionally ignored.

See the [permission hierarchy](https://docs.iamtelescope.net/concepts/auth/#permission-hierarchy)
for the complete role and permission matrix.

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
