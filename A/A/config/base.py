from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPO_DIR = BASE_DIR.parent

load_dotenv(REPO_DIR / ".env")
load_dotenv(BASE_DIR / ".env")
env = os.environ.get

# Debug mode settings
DEBUG = env("DEBUG", "true").lower() == "true"

# Deployment environment settings

deploy = env("deploy", "false").lower() == "true"
# Secret key for security purposes
SECRET_KEY = env(
    "SECRET_KEY",
    "unsafe-local-development-secret-key-with-more-than-32-characters",
)


# REDIS_LINK = env("REDIS_LINK")
# RABBIT_URI = env("RABBIT_URI")


MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

