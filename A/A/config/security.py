from .base import *

if DEBUG:

    CORS_ALLOW_ALL_ORIGINS = True
    ALLOWED_HOSTS = ["*"]
    INTERNAL_IPS = [
        "127.0.0.1",
    ]
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
else:
    CORS_ALLOWED_ORIGINS = [
        'http://127.0.0.1:5173',
        'http://localhost:5173',
        'http://abolfazlshahidi.ir',
        'https://abolfazlshahidi.ir',
    ]
    ALLOWED_HOSTS = [
        'localhost',
        '127.0.0.1',
        '.sslip.io',
        '.dokploy.com',
        'abolfazlshahidi.ir',
        '.abolfazlshahidi.ir',
    ]

    INTERNAL_IPS = [
        "127.0.0.1",
    ]
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    CSRF_TRUSTED_ORIGINS = [
        'https://abolfazlshahidi.ir',
        'https://back.abolfazlshahidi.ir',
        'http://abolfazlshahidi.ir',
        'http://back.abolfazlshahidi.ir',
    ]

SECURE_CROSS_ORIGIN_OPENER_POLICY = None
CORS_ALLOW_CREDENTIALS = False

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "django.log",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "file"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

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
