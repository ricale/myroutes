from mysite.settings.base import *
from mysite.settings.secrets import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

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
