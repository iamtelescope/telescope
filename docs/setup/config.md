# Config file options

With the configuration file, you can control certain aspects of the Telescope instance's operation.
The `TELESCOPE_CONFIG_FILE` variable specifies the configuration file that is used.

Please check the [config.py](https://github.com/iamtelescope/telescope/blob/main/backend/telescope/config.py) to get a detailed view of the default values used in the configuration and how they are merged with the values from the configuration files.

```yaml
auth:
  providers:
    github:
      # Enable or disable login via GitHub (https://github.com/iamtelescope/telescope/blob/main/backend/base/settings.py#L143-L154)
      enabled: false
      # Add users to the specified group on login (the group must exist)
      default_group: null
      # client_id, key, and secret should be obtained from GitHub (https://docs.allauth.org/en/dev/socialaccount/providers/github.html)
      client_id: ''
      key: ''
      secret: ''
      # If specified, users must belong to one of these organizations to log in.
      organizations: []

# These options are passed to Django settings
django:
  CSRF_TRUSTED_ORIGINS:
  - http://localhost:9898
  DATABASES:
    default:
      ENGINE: django.db.backends.sqlite3
      NAME: telescope-default-db.sqlite3
  DEBUG: false

# Passed to the Gunicorn web server instance (https://docs.gunicorn.org/en/latest/settings.html) (https://github.com/iamtelescope/telescope/blob/main/backend/app.py#L25)
gunicorn:
  bind: 127.0.0.1:9898
  max_requests: 50
  max_requests_jitter: 50
  timeout: 120
  workers: 8

# Options provided to vuejs app after loading config via `/ui/v1/config` handler
frontend:
    show_github_url: true  # show or not github url on top panel
    github_url: ""
    show_docs_url: true  # show or not docs url on top panel
    docs_url: ""

# Logging configuration (https://github.com/iamtelescope/telescope/blob/main/backend/telescope/log.py#L59)
logging:
  # Options: default, dev, or json
  format: default
  # Setup for log levels of different handlers
  levels:
    all: DEBUG
    django: DEBUG
    django.request: DEBUG
    django.template: INFO
    django.utils.autoreload: INFO
    telescope: DEBUG
```
