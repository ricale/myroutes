from myroutes.settings.base import *
from myroutes.settings.secrets import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Database
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'myroutes',
        'USER': 'root',
        'PASSWORD': DEFAULT_DATABASE_PASSWORD,
        'HOST': 'localhost',
        'PORT': '',
    }
}

CORS_ORIGIN_WHITELIST = [
    'localhost:8080',
    '127.0.0.1:8080'
]

CORS_ALLOW_CREDENTIALS = True
