# conftest.py (loyihangizning root direktoriyasiga qo'ying)
import os
import django
from django.conf import settings
from django.test.utils import get_runner

def pytest_configure():
    settings.configure(
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'rest_framework',
            'rest_framework_simplejwt',
            'drf_spectacular',
            'apps',  # sizning app nomingiz
        ],
        REST_FRAMEWORK={
            'DEFAULT_AUTHENTICATION_CLASSES': [
                'rest_framework_simplejwt.authentication.JWTAuthentication',
            ],
            'DEFAULT_PERMISSION_CLASSES': [
                'rest_framework.permissions.IsAuthenticated',
            ],
            'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
        },
        SECRET_KEY='test-secret-key',
        USE_TZ=True,
        ROOT_URLCONF='root.urls',  # sizning asosiy urls.py fayl yo'li
    )
    django.setup()