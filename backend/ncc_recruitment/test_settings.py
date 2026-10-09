from .settings import *  # noqa
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'test_db.sqlite3',
    }
}

# Send emails inline in tests so assertions on mail.outbox are deterministic.
EMAIL_SEND_IN_BACKGROUND = False
