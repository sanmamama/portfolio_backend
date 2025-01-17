from pathlib import Path
from .secrets import *
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# 開発環境
# DEBUG = True
# ALLOWED_HOSTS = ['*']
# CORS_ALLOW_ALL_ORIGINS = True

# 本番環境
DEBUG = False
ALLOWED_HOSTS = ['backend','sanmamama.com','www.sanmamama.com']
CORS_ORIGIN_WHITELIST = [
	'http://127.0.0.1:3000',
	'http://127.0.0.1:80',
	'http://127.0.0.1:8000',
]

ROOT_URLCONF = 'rest.urls'
WSGI_APPLICATION = 'rest.wsgi.application'

# Application definition
INSTALLED_APPS = [
	'api',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
	'corsheaders',
	'markdownx',
	'django_filters',
	
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
	
	'rest_framework',
	'rest_framework.authtoken',
	
    'dj_rest_auth',
    'dj_rest_auth.registration',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
	'corsheaders.middleware.CorsMiddleware',
	'allauth.account.middleware.AccountMiddleware',
	'django.middleware.locale.LocaleMiddleware',
]



TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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




# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'ja'

TIME_ZONE = 'Asia/Tokyo'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/



#開発環境
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'staticfiles')]
#本番環境
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_URL = '/static/'


#MEDIA_DIR
# mediaフォルダへの絶対パスを定義
MEDIA_DIR = BASE_DIR / "media"
MEDIA_ROOT = MEDIA_DIR
MEDIA_URL = "/media/"

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


AUTH_USER_MODEL = 'api.User'
SITE_ID = 1
ACCOUNT_AUTHENTICATION_METHOD = 'email'
#ACCOUNT_USERNAME_REQUIRED = False
#ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_REQUIRED = True              
ACCOUNT_UNIQUE_EMAIL = True                
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'  
ACCOUNT_ADAPTER = 'api.adapters.CustomAccountAdapter'

#EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # 開発中にコンソール
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True


AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 6,
	'DEFAULT_AUTHENTICATION_CLASSES': ('rest_framework.authentication.TokenAuthentication',),
	'DEFAULT_RENDERER_CLASSES': ('rest_framework.renderers.JSONRenderer',),
}

REST_AUTH = {
	'REGISTER_SERIALIZER': 'api.serializer.CustomRegisterSerializer',
}

MARKDOWNX_MARKDOWN_EXTENSIONS = [
    'markdown.extensions.extra',
    'markdown.extensions.toc',
    'markdown.extensions.nl2br',
]


