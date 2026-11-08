# Telescope Helm chart

A Helm chart for Telescope - web-based log viewer UI

```bash
helm lint ./helm
helm template telescope ./helm                   # render the manifests
helm install telescope ./helm --dry-run=client   # drop --dry-run=client to install
```

The chart creates the web Deployment and its Service, a ConfigMap holding the Telescope config built from the
`config.*` values, and, depending on the values below, the alert scheduler, a PVC for SQLite and a
PodDisruptionBudget. Secrets come from the existing Kubernetes secret named by `secretName`; the comments in
[values.yaml](values.yaml) list its keys.

## Alert scheduler

Alerts are evaluated by `manage.py telescope_scheduler`, started from the same image with the `scheduler` argument
(see `entrypoint.sh`). A lease in the database lets only one scheduler evaluate at a time, so extra replicas only add
failover.

- **PostgreSQL** (`database.type: postgresql`): the scheduler runs as its own Deployment,
  `<fullname>-scheduler`, with `scheduler.replicas` pods and the `Recreate` strategy. Its pods carry their own name
  label, so the web Service and the PodDisruptionBudget do not select them.
- **SQLite** (`database.type: sqlite`): the scheduler runs as a `scheduler` sidecar container in each web pod and
  shares that pod's database file. No scheduler Deployment is created and `scheduler.replicas` is not used.

With `scheduler.enabled: false` no scheduler runs: alerts can still be edited, but nothing evaluates them.

| Value | Default | Meaning |
|---|---|---|
| `scheduler.enabled` | `true` | Run the alert scheduler |
| `scheduler.replicas` | `1` | Scheduler pods on PostgreSQL (0-5) |
| `scheduler.resources` | requests 50m/192Mi, limits 500m/512Mi | Resources of the scheduler container |

## Alerts config

`config.alerts` becomes the `alerts` section of the Telescope config:

| Value | Default | Meaning |
|---|---|---|
| `config.alerts.enabled` | `true` | When false the scheduler keeps running but skips its ticks |
| `config.alerts.tick_seconds` | `15` | How often the scheduler evaluates |
| `config.alerts.allow_private_webhook_targets` | `false` | Allow webhook, Slack and PagerDuty targets on private or loopback addresses |
| `config.alerts.public_url` | `""` | Public Telescope URL for links in notifications, e.g. `https://telescope.example.com` |
| `config.alerts.email.host` | `""` | SMTP host for the email channel |
| `config.alerts.email.port` | `587` | SMTP port |
| `config.alerts.email.username` | `""` | SMTP user |
| `config.alerts.email.use_tls` | `true` | Use STARTTLS |
| `config.alerts.email.use_ssl` | `false` | Use implicit TLS |
| `config.alerts.email.from_email` | `telescope@localhost` | Sender address |

The SMTP password comes from the optional `ALERTS_SMTP_PASSWORD` key of the secret.
