from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),

    #(r'^i18n/', include('django.conf.urls.i18n')),

    (r'^', include('common.urls')),
    (r'^', include('products.urls')),
    (r'^', include('procurements.urls')),
    (r'^', include('main.urls')),
    (r'^', include(settings.AUTH_URLS)),
    (r'^inventory/', include('inventory.urls')),
    (r'^assets/', include('assets.urls')),
    (r'^search/', include('dynamic_search.urls')),
    (r'^import/', include('importer.urls')),
    (r'^movements/', include('movements.urls')),
    (r'^generic_photos/', include('photos.urls')),
    (r'^', include('company.urls')),
)

if settings.DEVELOPMENT:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += patterns('',
        (r'^django-inventory-site_media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': 'site_media', 'show_indexes': True}),
    )

    urlpatterns += staticfiles_urlpatterns()
    if 'rosetta' in settings.INSTALLED_APPS:
        urlpatterns += patterns('',
            url(r'^rosetta/', include('rosetta.urls'), name = "rosetta"),
        )
