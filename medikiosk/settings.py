"""
Django settings for medikiosk project.
"""

# System & Path Imports

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from BASE_DIR/.env or CWD .env
load_dotenv(BASE_DIR / '.env')
load_dotenv()

# Core Security & Debug Confi.

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-insecure-key-change-in-production')
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', '*').split(',')]

# Production Security Flags
if not DEBUG:
    SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'False').lower() in ('true', '1')
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1')
    CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'False').lower() in ('true', '1')
    SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '0'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
else:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_HSTS_SECONDS = 0

# Installed Applications

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'rest_framework',
    'corsheaders',
    # Local apps
    'kiosk',
    'sensors',
    'medicines',
    'doctor',
    'terminology',
]

# V1 & V2 Core Configuration
MEDIKIOSK_PRIVACY_MODE = os.getenv('MEDIKIOSK_PRIVACY_MODE', 'False').lower() in ('true', '1', 'yes')
DOCUMENT_CONFIDENCE_THRESHOLD = float(os.getenv('DOCUMENT_CONFIDENCE_THRESHOLD', '0.75'))

# Middleware Pipeline

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'medikiosk.urls'

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

WSGI_APPLICATION = 'medikiosk.wsgi.application'

# Database Confi. (SQLite dev / PostgreSQL prod)

if os.getenv('DB_ENGINE') == 'postgresql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'medikiosk'),
            'USER': os.getenv('DB_USER', 'medikiosk'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# Password Validation

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization & Time Zone

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static & Media Storage Confi.

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Security, CORS & CSRF Settings

CORS_ALLOW_ALL_ORIGINS = DEBUG
if not DEBUG and os.getenv('CORS_ORIGINS'):
    CORS_ALLOWED_ORIGINS = os.getenv('CORS_ORIGINS').split(',')

CSRF_TRUSTED_ORIGINS = os.getenv(
    'CSRF_ORIGINS',
    'http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000,http://127.0.0.1:3000'
).split(',')


# Django REST Framework Global & Throttling Confi.

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_CLASSES': [],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '10000/hour',
        'user': '10000/hour',
        'heavy_ai': '1000/minute',
        'sensor': '1000/minute',
    },
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# Sensor & Device Authentication Settings

SENSOR_AUTH_REQUIRED = os.getenv('SENSOR_AUTH_REQUIRED', 'False').lower() in ('true', '1', 'yes')
SENSOR_SECRET_KEY = os.getenv('SENSOR_SECRET_KEY', 'default-esp32-sensor-secret')

# AI Provider Confi. (Swappable)

# LLM
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'openai/gpt-4o')

# STT Provider: 'google', 'bhashini', 'whisper_local'
STT_PROVIDER = os.getenv('STT_PROVIDER', 'google')

# OCR Provider: 'google', 'tesseract', 'easyocr'
OCR_PROVIDER = os.getenv('OCR_PROVIDER', 'google')

# Google Cloud (used by both STT and OCR if selected)
GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')

# Sarvam AI (STT & TTS)
SARVAM_API_KEY = os.getenv('SARVAM_API_KEY', '')
SARVAM_STT_MODEL = os.getenv('SARVAM_STT_MODEL', 'saaras:v3')
SARVAM_TTS_MODEL = os.getenv('SARVAM_TTS_MODEL', 'bulbul:v1')

# IP Webcam (document scanner phone)
IP_WEBCAM_URL = os.getenv('IP_WEBCAM_URL', 'http://192.168.1.100:8080')

# Gemini LLM — multi-key failover
GEMINI_API_KEY_1 = os.getenv('GEMINI_API_KEY_1', '') or os.getenv('GEMINI_API_KEY', '')
GEMINI_API_KEY_2 = os.getenv('GEMINI_API_KEY_2', '')
GEMINI_API_KEY_3 = os.getenv('GEMINI_API_KEY_3', '')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-flash-latest')

# Qwen-VL local OCR model (offline)
QWEN_VL_MODEL = os.getenv('QWEN_VL_MODEL', 'Qwen/Qwen2-VL-2B-Instruct')

# Chatterbox TTS — offline model (weights loaded from HuggingFace cache)
CHATTERBOX_MODEL_DIR = os.getenv('CHATTERBOX_MODEL_DIR', '')
