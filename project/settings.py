"""
Django settings for zoksh project.
"""

from pathlib import Path
import os
import sys

# ============================================================
# BASE_DIR — Path موحّد
# ============================================================
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent.parent


# ============================================================
# Security
# ============================================================
SECRET_KEY = 'django-insecure-_678#zj)u2%di2-j-hj7q=&k964i@f1&rlz=fb50nda4d%z)t)'

DEBUG = True
# DEBUG = False

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "elbosely-group.up.railway.app",
]

CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "https://elbosely-group.up.railway.app",
]


# ============================================================
# Applications
# ============================================================
INSTALLED_APPS = [
    # Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'corsheaders',

    # Local
    'accounts',
    'catalog',
    'inventory',
    'dashboard',
    'payroll',
    'customers',
    'servicecenter',
    'supplier',
    'expenses',
    'finance',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',

    'corsheaders.middleware.CorsMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CORS_ALLOW_ALL_ORIGINS = True

AUTH_USER_MODEL = 'accounts.User'

ROOT_URLCONF = 'project.urls'


# ============================================================
# Templates
# ============================================================
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
            ],
        },
    },
]

WSGI_APPLICATION = 'project.wsgi.application'


# ============================================================
# Database — SQLite محلياً
# ============================================================
# DATABASES = {
#      'default': {
#          'ENGINE': 'django.db.backends.sqlite3',
#          'NAME': BASE_DIR / 'db.sqlite3',
#      }
#  }


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'railway',
        'USER': 'postgres',
        'PASSWORD': 'nwWfksmJVUfKPAzqlzMGslPkNuUgKENv',
        'HOST': 'hayabusa.proxy.rlwy.net',
        'PORT': '21945',
    }
}





# ============================================================
# Password validation
# ============================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ============================================================
# Internationalization
# ============================================================
LANGUAGE_CODE = 'ar'
TIME_ZONE = 'Africa/Cairo'
USE_I18N = True
USE_TZ = True
USE_L10N = True


# ============================================================
# Static & Media
# ============================================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Whitenoise — للـ production. في التطوير لا يحتاج ضبط خاص
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'



# ============================================================
# Telegram — تذكيرات العملاء
# ============================================================
import os

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8906763361:AAGG8BG6CbhJXr43JP9m8xlurKcaFHKCHGQ')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '5718328890')

# ============================================================
# Defaults
# ============================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ============================================================
# REST Framework
# ============================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
}


# ============================================================
# Session
# ============================================================
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'