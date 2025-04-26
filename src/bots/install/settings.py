import os
import bots
# Django settings for bots project.
PROJECT_PATH = os.path.abspath(os.path.dirname(bots.__file__))

#*******settings for sending bots error reports via email**********************************
MANAGERS = (    #bots will send error reports to the MANAGERS
    ('name_manager', 'adress@test.com'),
    )
EMAIL_HOST = 'localhost'             #Default: 'localhost'
EMAIL_PORT = '25'             #Default: 25
EMAIL_USE_TLS = False       #Default: False
EMAIL_HOST_USER = ''        #Default: ''. Username to use for the SMTP server defined in EMAIL_HOST. If empty, Django won't attempt authentication.
EMAIL_HOST_PASSWORD = ''    #Default: ''. PASSWORD to use for the SMTP server defined in EMAIL_HOST. If empty, Django won't attempt authentication.
#~ SERVER_EMAIL = 'user@gmail.com'           #Sender of bots error reports. Default: 'root@localhost'
#~ EMAIL_SUBJECT_PREFIX = ''   #This is prepended on email subject.

#*********database settings*************************
#SQLite database (default bots database)
DB_ENGINE = os.getenv('BOTS_DB_ENGINE', 'sqlite')

if DB_ENGINE == 'postgres':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': os.getenv('POSTGRES_DB', 'botsdb'),
            'USER': os.getenv('POSTGRES_USER', 'bots'),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'botsbots'),
            'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
            'PORT': os.getenv('POSTGRES_PORT', '5432'),
            'OPTIONS': {
                'sslmode': 'require',
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(PROJECT_PATH, 'botssys/sqlitedb/botsdb'),
        }
    }

#*********setting date/time zone and formats *************************
# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Amsterdam'

#~ *********language code/internationalization*************************
# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'
#~ LANGUAGE_CODE = 'nl'
USE_I18N = False

LOCALE_PATHS = (
    os.path.join(PROJECT_PATH, 'locale'),
    )

#*************************************************************************
#*********other django setting. please consult django docs.***************
#*************************************************************************
#*************************************************************************

#*********path settings*************************
STATIC_URL = '/media/'
MEDIA_URL = ''
STATIC_ROOT = PROJECT_PATH + '/'
MEDIA_ROOT = PROJECT_PATH + '/media/'
ROOT_URLCONF = 'bots.urls'
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/home'
LOGOUT_URL = '/logout/'
CORS_ORIGIN_ALLOW_ALL = True
#~ LOGOUT_REDIRECT_URL = #not such parameter; is set in urls.py
ALLOWED_HOSTS = ['*']

#*********sessions, cookies, log out time*************************
SESSION_EXPIRE_AT_BROWSER_CLOSE = True      #True: always log in when browser is closed
SESSION_COOKIE_AGE = 3600                   #seconds a user needs to login when no activity
SESSION_SAVE_EVERY_REQUEST = True           #if True: SESSION_COOKIE_AGE is interpreted as: since last activity

DEBUG = False
TEMPLATE_DEBUG = False
SITE_ID = 123
# Make this unique, and don't share it with anybody.
SECRET_KEY = 'm@-u37qiujmeqfbu$daaaaz)sp^7an4u@ddh=wfx9dd$$$zl2i*x9#awojdc'

#*******template handling and finding*************************************************************************
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(PROJECT_PATH, 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'bots.bots_context.set_context',
                'django.contrib.auth.context_processors.auth',
            ],
        },
    },
]

#*******includes for django*************************************************************************
#save uploaded file (=plugin) always to file. no path for temp storage is used, so system default is used.
FILE_UPLOAD_HANDLERS = [
    'django.core.files.uploadhandler.TemporaryFileUploadHandler',
]
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

INSTALLED_APPS = [
    'django.contrib.staticfiles',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
    'django.contrib.messages',
    'bots',
    'oauth2_provider',
    'corsheaders',
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'