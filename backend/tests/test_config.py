import copy

import pytest

from telescope.config import ConfigValidationError, SCHEMA, get_default_config, validate


def config_with_keycloak(**keycloak_updates):
    config = copy.deepcopy(get_default_config())
    config["django"]["SECRET_KEY"] = "test"
    config["auth"]["providers"]["keycloak"].update(
        {
            "enabled": True,
            "client_id": "telescope",
            "secret": "test-secret",
            "server_url": "https://keycloak.example/realms/telescope",
        }
    )
    config["auth"]["providers"]["keycloak"].update(keycloak_updates)
    return config


def test_default_keycloak_config_is_disabled():
    keycloak = get_default_config()["auth"]["providers"]["keycloak"]

    assert keycloak == {
        "enabled": False,
        "client_id": "",
        "secret": "",
        "server_url": "",
        "default_group": None,
    }


def test_keycloak_can_be_forced_when_enabled():
    config = config_with_keycloak(enabled=True)
    config["auth"]["force_auth_provider"] = "keycloak"

    validate(config, SCHEMA)


def test_forced_keycloak_must_be_enabled():
    config = get_default_config()
    config["django"]["SECRET_KEY"] = "test"
    config["auth"]["force_auth_provider"] = "keycloak"

    with pytest.raises(ConfigValidationError) as error:
        validate(config, SCHEMA)

    assert error.value.errors == [
        (
            "auth.force_auth_provider",
            "cannot be 'keycloak' if keycloak provider is not enabled",
        )
    ]


@pytest.mark.parametrize("field", ["client_id", "secret", "server_url"])
def test_enabled_keycloak_requires_non_empty_fields(field):
    config = config_with_keycloak(enabled=True, **{field: ""})

    with pytest.raises(ConfigValidationError) as error:
        validate(config, SCHEMA)

    assert (
        f"auth.providers.keycloak.{field}",
        "must be a non-empty string when keycloak provider is enabled",
    ) in error.value.errors


@pytest.mark.parametrize("field", ["client_id", "secret", "server_url"])
def test_enabled_keycloak_rejects_non_string_fields(field):
    config = config_with_keycloak(enabled=True, **{field: None})

    with pytest.raises(ConfigValidationError) as error:
        validate(config, SCHEMA)

    assert (
        f"auth.providers.keycloak.{field}",
        "must be a non-empty string when keycloak provider is enabled",
    ) in error.value.errors


def test_force_auth_provider_error_lists_keycloak():
    config = get_default_config()
    config["django"]["SECRET_KEY"] = "test"
    config["auth"]["force_auth_provider"] = "unknown"
    with pytest.raises(ConfigValidationError) as error:
        validate(config, SCHEMA)

    assert (
        "auth.force_auth_provider",
        "must be one of 'github', 'okta', or 'keycloak'",
    ) in error.value.errors

def test_empty_force_auth_provider_is_rejected():
    config = get_default_config()
    config["django"]["SECRET_KEY"] = "test"
    config["auth"]["force_auth_provider"] = ""

    with pytest.raises(ConfigValidationError) as error:
        validate(config, SCHEMA)

    assert (
        "auth.force_auth_provider",
        "must be one of 'github', 'okta', or 'keycloak'",
    ) in error.value.errors
