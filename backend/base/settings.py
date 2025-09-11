from pathlib import Path

from telescope.config import get_config
from telescope.log import LogConfig

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

CONFIG = get_config()

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
    "django.contrib.sites",
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

if CONFIG["auth"]["providers"]["keycloak"]["enabled"]:
    INSTALLED_APPS.append("allauth.socialaccount.providers.openid_connect")

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

LOGIN_URL = "/login"

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

if CONFIG["auth"]["providers"]["keycloak"]["enabled"]:
    keycloak_config = CONFIG["auth"]["providers"]["keycloak"]
    
    server_url = keycloak_config['server_url']
    realm = keycloak_config['realm']
    
    oidc_endpoint = f"{server_url}/realms/{realm}/.well-known/openid-configuration"
    
    app_config = {
        "provider_id": "keycloak",
        "name": "Keycloak",
        "client_id": keycloak_config["client_id"],
        "settings": {
            "server_url": oidc_endpoint,
        },
    }
    
    if keycloak_config.get("client_secret"):
        app_config["secret"] = keycloak_config["client_secret"]
        
    SOCIALACCOUNT_PROVIDERS["openid_connect"] = {
        "APPS": [app_config],
        "OAUTH_PKCE_ENABLED": True,
    }


SESSION_COOKIE_AGE = CONFIG["django"].get("SESSION_COOKIE_AGE", 1209600)
SITE_ID = 1
SITE_DOMAIN = CONFIG["django"]["SITE_DOMAIN"]
SITE_NAME = CONFIG["django"]["SITE_NAME"]

LOGIN_REDIRECT_URL = "/"

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"

if CONFIG["django"].get("SECURE_PROXY_SSL_HEADER"):
    SECURE_PROXY_SSL_HEADER = (
        django_conf["SECURE_PROXY_SSL_HEADER"].get("header"),
        django_conf["SECURE_PROXY_SSL_HEADER"].get("value"),
    )


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = LogConfig(config=CONFIG["logging"]).as_dict()
