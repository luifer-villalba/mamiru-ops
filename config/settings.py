import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv
from django.urls import reverse_lazy

# Load .env file if present (development only)
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
_INSECURE_KEY = "django-insecure-change-me-in-production"
SECRET_KEY = os.environ.get("SECRET_KEY", _INSECURE_KEY)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", "False") == "True"

if not DEBUG and (not SECRET_KEY or SECRET_KEY == _INSECURE_KEY):
    raise RuntimeError(
        "SECRET_KEY must be set to a secure value when DEBUG is False."
    )

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

if "100.64.0.2" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append("100.64.0.2")

for railway_host_var in ("RAILWAY_PUBLIC_DOMAIN", "RAILWAY_PRIVATE_DOMAIN"):
    railway_host = os.environ.get(railway_host_var, "").strip()
    if railway_host and railway_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(railway_host)

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

# Application definition

INSTALLED_APPS = [
    "unfold",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "catalog",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "config.middleware.HealthcheckBypassMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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

WSGI_APPLICATION = "config.wsgi.application"

# Database – use DATABASE_URL env var (required in production / Docker)
_default_db_url = "sqlite:///" + str(BASE_DIR / "db.sqlite3")
DATABASES = {
    "default": dj_database_url.config(
        default=os.environ.get("DATABASE_URL", _default_db_url),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "es"
LANGUAGES = [
    ("es", "Español"),
]
TIME_ZONE = "America/Asuncion"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = os.environ.get("STATIC_URL", "/static/")
STATIC_ROOT = os.environ.get("STATIC_ROOT", str(BASE_DIR / "staticfiles"))
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Media files (uploaded images)
MEDIA_URL = os.environ.get("MEDIA_URL", "/media/")
MEDIA_ROOT = os.environ.get("MEDIA_ROOT", str(BASE_DIR / "media"))

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

# Unfold admin theme
UNFOLD = {
    "SITE_TITLE": "Mamiru Ops",
    "SITE_HEADER": "Mamiru Ops",
    "SITE_SUBHEADER": "Catálogo interno",
    "SITE_SYMBOL": "storefront",
    "SITE_URL": None,
    "SHOW_HISTORY": True,
    "DASHBOARD_CALLBACK": "catalog.dashboard.admin_dashboard_callback",
    "SHOW_VIEW_ON_SITE": False,
    "SHOW_BACK_BUTTON": True,
    "BORDER_RADIUS": "6px",
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "Catálogo",
                "separator": True,
                "collapsible": False,
                "items": [
                    {
                        "title": "Productos",
                        "icon": "inventory_2",
                        "link": reverse_lazy("admin:catalog_product_changelist"),
                    },
                    {
                        "title": "Categorías",
                        "icon": "category",
                        "link": reverse_lazy("admin:catalog_category_changelist"),
                    },
                    {
                        "title": "Proveedores",
                        "icon": "local_shipping",
                        "link": reverse_lazy("admin:catalog_supplier_changelist"),
                    },
                ],
            },
            {
                "title": "Sistema",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Usuarios",
                        "icon": "people",
                        "link": reverse_lazy("admin:auth_user_changelist"),
                    },
                    {
                        "title": "Grupos",
                        "icon": "groups",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                    },
                ],
            },
        ],
    },
}
