# -*- encoding: utf-8 -*-
# Django settings for django-inventory project.
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "./"))

sys.path.append(os.path.join(PROJECT_ROOT, 'modules'))
sys.path.append(os.path.join(PROJECT_ROOT, 'customization_apps'))
sys.path.append(os.path.join(PROJECT_ROOT, 'apps'))
sys.path.append(os.path.join(PROJECT_ROOT, 'shared_apps'))
sys.path.append(os.path.join(PROJECT_ROOT, '3rd_party_apps'))

PROJECT_TITLE = 'ΠΣ Κτηματολογίου υποδομών ΠΣΔ & υποδομών ΤΠΕ Σχολείων'
PROJECT_NAME = 'django_inventory'

DEBUG = True
DEVELOPMENT = True
TEMPLATE_DEBUG = DEBUG
ADMINS = (
        # ('Your Name', 'your_email@domain.com'),
)

LOGGING = {
    'version': 1,

    'handlers': {
        'console':{
            'level':'DEBUG',
            'class':'logging.StreamHandler',
        },
    },
    'loggers': {
        'apps': {
            'handlers': ['console',],
            'level': 'INFO',
            },
        'django.db.backends': {
            'handlers': ['console',],
            'level': 'INFO',
            },
        'permissions': {
            'handlers': ['console',],
            'level': 'INFO',
            },
        }
    }

MANAGERS = ADMINS

AUTH_BACKEND = 'auth_passwd'
AUTH_URLS = AUTH_BACKEND + '.urls'
AUTH_PROFILE_MODULE = AUTH_BACKEND+'.UserProfile'

DATABASES = {
    'non-default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': os.path.join(PROJECT_ROOT, "%s.sqlite" % PROJECT_NAME),     # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    },
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'django_inventory',
        #'USER': 'USERNAME',       # Not used with sqlite3.
        #'PASSWORD': 'USERPASSWORD',   # Not used with sqlite3.
        #'HOST': 'localhost',      # Set to empty string for localhost.
        'PORT': '',               # Set to empty string for default.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Athens'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en'

ugettext = lambda s: s

LANGUAGES = (
    # ('es', ugettext('Spanish')),
    ('en', ugettext('English')),
    # ('ru', ugettext('Russian')),
    ('el', ugettext('Greek')),
)

SITE_ID = 1

DATE_INPUT_FORMATS = ('%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d')
DATE_FORMAT = '%d/%m/%Y'
# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'site_media/')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/django-inventory-site_media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = MEDIA_URL + 'admin_media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '4#8p2r=zfa=t@3@@v5v*)i=kvnuyxae_yyvqkyv4!opcwad6@+'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    ('django.template.loaders.cached.Loader', (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    )),
)

MIDDLEWARE_CLASSES = [
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'middleware.login_required_middleware.LoginRequiredMiddleware',
    'pagination.middleware.PaginationMiddleware',
]

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
     os.path.join(PROJECT_ROOT, 'templates')
)

INSTALLED_APPS = [
    'grappelli',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.staticfiles',
    'django.contrib.formtools',
    'pagination',
    'photologue',
    'photos',
    'common',
    'products',
    'procurements',
    'company',
    'generic_views',
    'inventory',
    'assets',
    'dynamic_search',
    'importer',
    'movements',
    'main',
    'web_theme',
    'ajax_select',
    AUTH_BACKEND,
]


TEMPLATE_CONTEXT_PROCESSORS = [
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    'django.core.context_processors.request',
    'django.core.context_processors.static',
    'main.cart_utils.in_context',
    "grappelli.context_processors.admin_template_path",
    'django.contrib.messages.context_processors.messages',
]

AJAX_LOOKUP_CHANNELS = {
    'department': ('company.lookups', 'DepartmentLookup'),
    'location': ('company.lookups', 'LocationLookup'), # searches by department!
    'location_by_role': ('company.lookups', 'RoleLocationLookup'),
    'product': ('products.lookups', 'ItemTemplateLookup'),
    'categories': ('products.lookups', 'ItemCategoryLookup'),
    'product_part': ('products.lookups', 'ProductPartLookup'),
    'product_specs': ('products.lookups', 'ProductSpecsLookup'),
    'manufacturer': ('products.lookups', 'ManufacturerLookup'),
    'item': ('assets.lookups', 'ItemLookup'),
    'contracts': ('procurements.lookups', 'ContractLookup'),
    'supplier_name': ('common.lookups', 'SupplierLookup'),
    'supplier_vat': ('common.lookups', 'SupplierVATLookup'),
}
AJAX_SELECT_BOOTSTRAP = False
AJAX_SELECT_INLINES = False

#===== Configuration options ===============
#--------- Grappelli ----------------
GRAPPELLI_ADMIN_TITLE = PROJECT_TITLE
#--------- Django -------------------
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
#-------- LoginRequiredMiddleware ----------
LOGIN_EXEMPT_URLS = (
    r'^favicon\.ico$',
    r'^about\.html$',
    r'^legal/', # allow the entire /legal/* subsection
    )

if AUTH_BACKEND == 'auth_passwd':
    LOGIN_EXEMPT_URLS = LOGIN_EXEMPT_URLS + ( \
    r'^accounts/register/$',
    r'^accounts/register/complete/$',
    r'^accounts/register/closed/$',

    r'^accounts/activate/complete/',
    r'^accounts/activate/(?P<activation_key>\w+)/$',

    r'^password/reset/$',
    r'^password/reset/confirm/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
    r'^password/reset/complete/$',
    r'^password/reset/done/$',
    )

#--------- Generic photos --------------
#PHOTOS_MAX_PHOTO_SIZE = 1000000
#INVENTORY_MAX_TEMPLATE_PHOTOS = 5
#ASSETS_MAX_ASSET_PHOTOS = 5
#ASSETS_MAX_PERSON_PHOTOS = 5
#--------- Pagination ------------------
PAGINATION_DEFAULT_PAGINATION = 50
#--------- Web theme app ---------------
WEB_THEME = 'warehouse'

STATIC_URL= '/static/'
# Place to copy static files into: Do not commit this, it is generated!
STATIC_ROOT = './staticfiles/'
# USE_ETAGS = False
USE_THOUSAND_SEPARATOR = True

#======== End of configuration options =======
try:
    from settings_local import *
except ImportError:
    pass


if DEVELOPMENT:
    INTERNAL_IPS = ('127.0.0.1',)

    TEMPLATE_LOADERS = (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    )
    LOGIN_EXEMPT_URLS = LOGIN_EXEMPT_URLS + ( r'^django-inventory-site_media/',)

    try:
        import rosetta
        INSTALLED_APPS.append('rosetta')
    except ImportError:
        pass
        #print "rosetta is not installed"

    try:
        import django_extensions
        INSTALLED_APPS.append('django_extensions')
    except ImportError:
        pass
        #print "django_extensions is not installed"

    try:
        import debug_toolbar
        INSTALLED_APPS.append('debug_toolbar')
    except ImportError:
        pass
        print "debug_toolbar is not installed"

    TEMPLATE_CONTEXT_PROCESSORS.append("django.core.context_processors.debug")

    WSGI_AUTO_RELOAD = True
    if 'debug_toolbar' in INSTALLED_APPS:
        MIDDLEWARE_CLASSES.append('debug_toolbar.middleware.DebugToolbarMiddleware')
        DEBUG_TOOLBAR_CONFIG={
            'INTERCEPT_REDIRECTS' : False,
        }

#eof
