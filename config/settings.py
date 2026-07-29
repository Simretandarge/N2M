"""
Django settings for Next 251 Media (N2M).
SQLite for dev; production-ready for PostgreSQL.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env from project root (for EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, etc.)
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / '.env')
except ImportError:
    pass

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-secret-key-change-in-production')

_debug_raw = os.environ.get('DEBUG', os.environ.get('DJANGO_DEBUG', '0'))
DEBUG = str(_debug_raw).strip().lower() in ('1', 'true', 'yes', 'on')

# Comma-separated; include apex and www (e.g. next251.com,www.next251.com) or Django returns 400 DisallowedHost.
ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    if h.strip()
]

# CSRF for admin/forms when using HTTPS; add production URLs via CSRF_TRUSTED_ORIGINS in .env (comma-separated).
CSRF_TRUSTED_ORIGINS = [
    'http://127.0.0.1:8000',
    'http://localhost:8000',
]
_extra_csrf = os.environ.get('CSRF_TRUSTED_ORIGINS', '').strip()
if _extra_csrf:
    CSRF_TRUSTED_ORIGINS.extend(
        o.strip() for o in _extra_csrf.split(',') if o.strip()
    )

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'content',
    'accounts',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'content.context_processors.site_meta',
                'accounts.context_processors.user_role',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database:
# - Local/dev default: SQLite
# - cPanel/prod: set USE_POSTGRES=1 and provide DB_NAME/DB_USER/DB_PASSWORD
USE_POSTGRES = os.environ.get('USE_POSTGRES', '').lower() in ('1', 'true', 'yes')
if USE_POSTGRES:
    db_host = os.environ.get('DB_HOST', 'localhost').strip()
    db_port = os.environ.get('DB_PORT', '5432').strip()
    db_sslmode = os.environ.get('DB_SSLMODE', '').strip()
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', ''),
            'USER': os.environ.get('DB_USER', ''),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            # On cPanel same-server deployments, localhost is usually correct.
            'HOST': db_host,
            'PORT': db_port,
        }
    }
    if db_sslmode:
        DATABASES['default']['OPTIONS'] = {'sslmode': db_sslmode}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Site meta for templates and SEO
SITE_NAME = 'Next 251 Media'
SITE_TAGLINE = 'Technology Through a Clear Lens.'
SITE_DESCRIPTION = (
    'Technology, AI, Business, Startups & Innovation - explained clearly through '
    'an Ethiopian, African and global lens.'
)
NEWSLETTER_PRODUCT_NAME = 'The Next 251 Brief'
# Public UI: optional stable boosts for like/save/view display (see content.views; Django admin shows real counts).
DISPLAY_COUNT_BOOST_ENABLED = os.environ.get('DISPLAY_COUNT_BOOST_ENABLED', '1').lower() in ('1', 'true', 'yes')
DISPLAY_COUNT_SALT = os.environ.get('DISPLAY_COUNT_SALT', '')
# Per-item additive boost (stable hash from pk + kind + salt).
DISPLAY_LIKE_BOOST_MIN = int(os.environ.get('DISPLAY_LIKE_BOOST_MIN', '15'))
DISPLAY_LIKE_BOOST_MAX = int(os.environ.get('DISPLAY_LIKE_BOOST_MAX', '45'))
DISPLAY_SAVE_BOOST_MIN = int(os.environ.get('DISPLAY_SAVE_BOOST_MIN', '3'))
DISPLAY_SAVE_BOOST_MAX = int(os.environ.get('DISPLAY_SAVE_BOOST_MAX', '6'))
# Public view counts: base bump on real views, then floor at (public likes + gap) so views stay plausible vs likes.
DISPLAY_VIEW_BOOST_MIN = int(os.environ.get('DISPLAY_VIEW_BOOST_MIN', '22'))
DISPLAY_VIEW_BOOST_MAX = int(os.environ.get('DISPLAY_VIEW_BOOST_MAX', '72'))
DISPLAY_VIEW_OVER_LIKE_MIN = int(os.environ.get('DISPLAY_VIEW_OVER_LIKE_MIN', '12'))
DISPLAY_VIEW_OVER_LIKE_MAX = int(os.environ.get('DISPLAY_VIEW_OVER_LIKE_MAX', '52'))
# Wait this many minutes after publish/post before boosted counts appear (per-item stable value in range).
DISPLAY_COUNT_BOOST_DELAY_MIN_MINUTES = int(os.environ.get('DISPLAY_COUNT_BOOST_DELAY_MIN_MINUTES', '30'))
DISPLAY_COUNT_BOOST_DELAY_MAX_MINUTES = int(os.environ.get('DISPLAY_COUNT_BOOST_DELAY_MAX_MINUTES', '60'))
# Optional: canonical site URL for links in emails when there is no HTTP request (cron). Example: https://www.next251.com
SITE_PUBLIC_BASE_URL = os.environ.get('SITE_PUBLIC_BASE_URL', '').strip().rstrip('/')
# Newsletter digest footer — follow links (override via .env if URLs change)
SOCIAL_LINKEDIN_URL = os.environ.get(
    'SOCIAL_LINKEDIN_URL',
    'https://www.linkedin.com/company/next251-media-n2m/about/?viewAsMember=true',
).strip()
SOCIAL_INSTAGRAM_URL = os.environ.get(
    'SOCIAL_INSTAGRAM_URL',
    'https://www.instagram.com/next251media/',
).strip()
SOCIAL_FACEBOOK_URL = os.environ.get(
    'SOCIAL_FACEBOOK_URL',
    'https://web.facebook.com/people/Next251-Media/61588122357942/'
    '?rdid=lJ5zIBE0nXxgrnK0&share_url=https%3A%2F%2Fweb.facebook.com%2Fshare%2F1AhUPMiwDS%2F%3F_rdc%3D1%26_rdr',
).strip()

# Auth: signup, signin, role-based dashboard
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'accounts:dashboard'
LOGOUT_REDIRECT_URL = 'content:home'

# Email
# - Default (dev): emails are printed in the terminal (runserver). Look there for reset links.
# - To send real emails: set USE_REAL_EMAIL=1 and configure SMTP below.
# no-reply@: used for password reset, registration, and other system emails (recipients don't reply).
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'no-reply@next251.com')
# Newsletter: "from" address when sending the newsletter to subscribers.
NEWSLETTER_FROM_EMAIL = os.environ.get('NEWSLETTER_FROM_EMAIL', 'newsletter@next251.com')
# Optional: use a separate SMTP account for sending newsletters (e.g. newsletter@next251.com).
# If set, newsletter is sent with these credentials; otherwise the default EMAIL_* is used.
NEWSLETTER_EMAIL_HOST_USER = os.environ.get('NEWSLETTER_EMAIL_HOST_USER', '')
NEWSLETTER_EMAIL_HOST_PASSWORD = os.environ.get('NEWSLETTER_EMAIL_HOST_PASSWORD', '')
# Send a short welcome email when someone is newly added as a newsletter subscriber
NEWSLETTER_SEND_WELCOME_EMAIL = os.environ.get('NEWSLETTER_SEND_WELCOME_EMAIL', '1').lower() in ('1', 'true', 'yes')
# Weekly digest schedule + content cap:
# - WEEKLY_DIGEST_SEND_WEEKDAY: Monday=0 ... Sunday=6 (default Friday=4)
# - WEEKLY_DIGEST_SEND_HOUR / MINUTE are interpreted in WEEKLY_DIGEST_TIMEZONE
# - WEEKLY_DIGEST_SEND_WINDOW_MINUTES allows sending only within this window
# - WEEKLY_DIGEST_MAX_ITEMS caps how many newsletter issues are included in one digest
WEEKLY_DIGEST_TIMEZONE = os.environ.get('WEEKLY_DIGEST_TIMEZONE', 'Africa/Addis_Ababa')
WEEKLY_DIGEST_SEND_WEEKDAY = int(os.environ.get('WEEKLY_DIGEST_SEND_WEEKDAY', '4'))
WEEKLY_DIGEST_SEND_HOUR = int(os.environ.get('WEEKLY_DIGEST_SEND_HOUR', '20'))
WEEKLY_DIGEST_SEND_MINUTE = int(os.environ.get('WEEKLY_DIGEST_SEND_MINUTE', '0'))
WEEKLY_DIGEST_SEND_WINDOW_MINUTES = int(os.environ.get('WEEKLY_DIGEST_SEND_WINDOW_MINUTES', '120'))
WEEKLY_DIGEST_MAX_ITEMS = int(os.environ.get('WEEKLY_DIGEST_MAX_ITEMS', '12'))

# SMTP connection parameters are always loaded from the environment so newsletter-only SMTP
# (NEWSLETTER_EMAIL_HOST_USER / PASSWORD + get_connection) works even when the default
# EMAIL_BACKEND is still the console for local dev.
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'true').lower() in ('1', 'true', 'yes')
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'false').lower() in ('1', 'true', 'yes')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

if os.environ.get('USE_REAL_EMAIL', '').lower() in ('1', 'true', 'yes'):
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
