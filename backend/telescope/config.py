import os
import collections.abc

import yaml
import jsonschema


class ConfigValidationError(RuntimeError):
    def __init__(
        self,
        message,
        errors=None,
    ):
        self.message = message
        self.errors = errors or []

    def __str__(self):
        return self.message + ": " + ", ".join([f"{i[0]}: {i[1]}" for i in self.errors])

    def __repr__(self):
        return str(self)


JSONSchemaValidator = jsonschema.Draft7Validator


SCHEMA = {
    "type": "object",
    "properties": {
        "gunicorn": {
            "type": "object",
        },
        "auth": {
            "type": "object",
            "properties": {
                "providers": {
                    "type": "object",
                },
                "force_github_auth": {
                    "type": "boolean",
                },
                "enable_testing_auth": {
                    "type": "boolean",
                },
                "testing_auth_username": {
                    "type": "string",
                },
            },
        },
        "limits": {
            "max_saved_views_per_user": {
                "type": "integer",
            },
        },
        "django": {
            "type": "object",
            "properties": {
                "SECRET_KEY": {
                    "type": "string",
                },
            },
            "required": ["SECRET_KEY"],
            "additionalProperties": True,
        },
        "logging": {
            "type": "object",
        },
        "frontend": {
            "type": "object",
            "properties": {
                "github_url": {
                    "type": "string",
                },
                "show_github_url": {
                    "type": "boolean",
                },
                "docs_url": {
                    "type": "string",
                },
                "show_docs_url": {
                    "type": "boolean",
                },
                "base_url": {
                    "type": "string",
                },
            },
        },
        "additionalProperties": True,
    },
}


class YamlLoader(yaml.SafeLoader):
    @classmethod
    def init_constructors(cls):
        cls.add_constructor("!env", cls.env)

    def __init__(self, stream):
        super(YamlLoader, self).__init__(stream)

    def env(self, node):
        env_var = self.construct_scalar(node)
        env_value = os.getenv(env_var)
        return env_value


YamlLoader.init_constructors()


def validate(config, schema):
    errors = []
    errors_generator = JSONSchemaValidator(schema).iter_errors(config)
    for error in sorted(errors_generator, key=jsonschema.exceptions.relevance):
        path = ".".join(map(str, error.absolute_path))
        errors.append((path, error.message))

    if not errors:
        if config["auth"]["force_auth_provider"]:
            provider = config["auth"]["force_auth_provider"]
            if provider not in ["github", "okta"]:
                errors.append(
                    (
                        "auth.force_auth_provider",
                        "must be either 'github' or 'okta'",
                    )
                )
            elif not config["auth"]["providers"].get(provider, {}).get("enabled"):
                errors.append(
                    (
                        "auth.force_auth_provider",
                        f"cannot be '{provider}' if {provider} provider is not enabled",
                    )
                )

    if errors:
        raise ConfigValidationError(message="Malformed configuration", errors=errors)


def merge_dicts(first, second):
    def _update(orig, update):
        for key, value in update.items():
            if isinstance(value, collections.abc.Mapping):
                orig[key] = _update(orig.get(key, {}), value)
            else:
                orig[key] = update[key]
        return orig

    _result = {}
    _update(_result, first)
    _update(_result, second)
    return _result


def get_default_config():
    return {
        "gunicorn": {
            "bind": "127.0.0.1:9898",
            "workers": 8,
            "timeout": 120,
            "max_requests": 50,
            "max_requests_jitter": 50,
        },
        "django": {
            "CSRF_TRUSTED_ORIGINS": [
                "http://localhost:9898",
            ],
            "DEBUG": False,
            "DATABASES": {
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": "telescope-default-db.sqlite3",
                },
            },
        },
        "limits": {
            "max_saved_views_per_user": 0,
        },
        "auth": {
            "providers": {
                "github": {
                    "enabled": False,
                    "key": "",
                    "organizations": [],
                    "default_group": None,
                },
                "okta": {
                    "enabled": False,
                    "client_id": "",
                    "secret": "",
                    "base_url": "",
                    "default_group": None,
                    "scope": "openid profile email",
                    "pkce_enabled": True,
                },
            },
            "force_auth_provider": None,
            "local_login_secret_path": None,
            "enable_testing_auth": False,
            "testing_auth_username": "telescope",
        },
        "frontend": {
            "github_url": "https://github.com/iamtelescope/telescope",
            "docs_url": "https://iamtelescope.github.io/telescope/docs",
            "show_docs_url": True,
            "base_url": "",
        },
        "logging": {
            "format": "default",
            "levels": {
                "django": "DEBUG",
                "django.request": "DEBUG",
                "django.template": "INFO",
                "django.utils.autoreload": "INFO",
                "telescope": "DEBUG",
                "all": "DEBUG",
            },
        },
    }


def get_config():
    config_file = os.environ.get("TELESCOPE_CONFIG_FILE")
    config = {}
    default_config = get_default_config()

    if config_file:
        with open(config_file) as fd:
            config = yaml.load(fd, Loader=YamlLoader)
    config = merge_dicts(default_config, config)
    validate(config, SCHEMA)
    return config
