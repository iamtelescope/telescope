# Telescope Helm chart

A Helm chart for Telescope - web-based log viewer UI.

## Keycloak OIDC

Enable Keycloak for browser login with one confidential client in one realm:

```yaml
config:
  auth:
    providers:
      keycloak:
        enabled: true
        client_id: "telescope"
        server_url: "https://sso.example/realms/telescope"
        default_group: "telescope-users"
    force_auth_provider: keycloak # optional
secretName: telescope-secrets
```

For a read-only Keycloak audience, set `default_group` to an exact group name,
for example `"read only"`. Create the group in Telescope and grant it the
`viewer` role on each source and connection for configuration-only access.
For log queries without edit, delete, or grant permissions, use the `user`
role on the required sources; it grants `source_read` and `source_use`. Use
the connection `viewer` role for connection visibility. Creating sources
additionally requires the global `global_create_source` permission and the
connection `user` role, which grants `connection_use`. The chart does not map
Keycloak groups or roles, so `default_group` is the single application-side
group assigned after a successful Keycloak login.

Do not put the Keycloak client secret or the emergency local-login path in
`values.yaml`. The chart reads them from the Kubernetes Secret as
`KEYCLOAK_SECRET` and `LOCAL_LOGIN_SECRET_PATH`:

Create a local environment file with restrictive permissions, populate it
using an editor, and create the Kubernetes Secret without putting secret
values in command-line arguments:

```bash
install -m 600 /dev/null telescope-secrets.env
${EDITOR:-vi} telescope-secrets.env
kubectl create secret generic telescope-secrets \
  --from-env-file=telescope-secrets.env && \
  rm -f telescope-secrets.env
```

The file should contain:

```text
DJANGO_SECRET_KEY=<django-secret>
KEYCLOAK_SECRET=<keycloak-client-secret>
LOCAL_LOGIN_SECRET_PATH=<emergency-login-path>
```

`KEYCLOAK_SECRET` is required when Keycloak is enabled. Set
`LOCAL_LOGIN_SECRET_PATH` only when emergency local login is needed.

Register this exact redirect URI in the Keycloak client:

```text
https://<public-host>/login/oidc/keycloak/login/callback/
```

If `config.frontend.base_url` is set, include that subpath before `/login/`.
The client must have Client authentication and Standard Flow enabled, with PKCE
method `S256`. Telescope discovers the realm endpoints from
`<server_url>/.well-known/openid-configuration`.
