import pytest
from django.contrib.auth.models import User
from django.test import Client


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser("root", password="secret-pass")


def test_login_page_has_labels_title_and_sign_in(superuser):
    html = Client().get("/login").content.decode()
    assert "<title>Sign in · Telescope</title>" in html
    assert '<label for="id_username">Username</label>' in html
    assert '<label for="id_password">Password</label>' in html
    assert 'data-testid="login-submit">Sign in</button>' in html


def test_login_error_is_announced(superuser):
    html = (
        Client()
        .post("/login", {"username": "root", "password": "wrong"})
        .content.decode()
    )
    assert 'class="form-errors" role="alert">Please enter a correct username' in html


def test_logout_page_offers_cancel(superuser):
    client = Client()
    client.force_login(superuser)
    html = client.get("/logout").content.decode()
    assert "Log out of Telescope?" in html
    assert ">Cancel</a>" in html


def test_setup_page_says_passwords_do_not_match(db):
    html = (
        Client()
        .post(
            "/setup",
            {"username": "root", "password": "a", "password_repeat": "b"},
        )
        .content.decode()
    )
    assert '<label for="id_password_repeat">Password (repeat)</label>' in html
    assert "Passwords do not match" in html
