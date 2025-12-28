from pathlib import Path

from telescope.config import get_config
from telescope.log import LogConfig

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

CONFIG = get_config()

# Base URL configuration for deployment under subpaths
BASE_URL = CONFIG["frontend"].get("base_url", "").rstrip("/")

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = CONFIG["django"]["SECRET_KEY"]

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = CONFIG["django"].get("DEBUG", False)

ALLOWED_HOSTS = CONFIG["django"].get("ALLOWED_HOSTS", [])

# Application definition

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    "telescope",
]

if CONFIG["auth"]["providers"]["github"]["enabled"]:
    INSTALLED_APPS.append("allauth.socialaccount.providers.github")

if CONFIG["auth"]["providers"]["okta"]["enabled"]:
    INSTALLED_APPS.append("allauth.socialaccount.providers.okta")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]
if CONFIG["auth"]["enable_testing_auth"]:
    MIDDLEWARE.append("telescope.auth.middleware.TestingAuthMiddleware")

MIDDLEWARE.extend(
    [
        "django.contrib.messages.middleware.MessageMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
        "allauth.account.middleware.AccountMiddleware",
    ]
)

CORS_ALLOW_ALL_ORIGINS = True
CSRF_TRUSTED_ORIGINS = CONFIG["django"].get("CSRF_TRUSTED_ORIGINS", [])

# Apply base URL configuration
if BASE_URL:
    FORCE_SCRIPT_NAME = BASE_URL

ROOT_URLCONF = "base.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

LOGIN_URL = f"{BASE_URL}/login"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "telescope.utils.DefaultJSONRenderer",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "telescope.auth.token.TokenAuth",
    ),
}

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

WSGI_APPLICATION = "base.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = CONFIG["django"]["DATABASES"]

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Provider specific settings
SOCIALACCOUNT_PROVIDERS = {}
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_EMAIL_REQUIRED = False

if CONFIG["auth"]["providers"]["github"]["enabled"]:
    github_config = {
        "APP": {
            "client_id": CONFIG["auth"]["providers"]["github"]["client_id"],
            "secret": CONFIG["auth"]["providers"]["github"]["secret"],
            "key": CONFIG["auth"]["providers"]["github"].get("key", ""),
        },
    }
    if CONFIG["auth"]["providers"]["github"].get("organizations"):
        github_config["SCOPE"] = ["read:org"]

    SOCIALACCOUNT_PROVIDERS["github"] = github_config

if CONFIG["auth"]["providers"]["okta"]["enabled"]:
    okta_config = {
        "APP": {
            "client_id": CONFIG["auth"]["providers"]["okta"]["client_id"],
            "secret": CONFIG["auth"]["providers"]["okta"]["secret"],
        },
        "OKTA_BASE_URL": CONFIG["auth"]["providers"]["okta"]["base_url"],
        "SCOPE": CONFIG["auth"]["providers"]["okta"]
        .get("scope", "openid profile email")
        .split(),
    }
    if CONFIG["auth"]["providers"]["okta"].get("pkce_enabled", True):
        okta_config["OAUTH_PKCE_ENABLED"] = True

    SOCIALACCOUNT_PROVIDERS["okta"] = okta_config

if CONFIG["django"].get("SECURE_PROXY_SSL_HEADER"):
    header_config = CONFIG["django"]["SECURE_PROXY_SSL_HEADER"]
    if isinstance(header_config, list) and len(header_config) == 2:
        SECURE_PROXY_SSL_HEADER = tuple(header_config)

LOGIN_REDIRECT_URL = f"{BASE_URL}/"

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = LogConfig(config=CONFIG["logging"]).as_dict()
