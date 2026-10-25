"""URL configuration for the storefront project."""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = 'Storefront Admin'
admin.site.index_title = 'Store management'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('playground/', include('playground.urls')),
    path('store/', include('store.urls')),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.jwt')),
    path('', include('shop.urls')),
]

# Debug toolbar is only wired up when it is actually installed (see settings.py).
if settings.DEBUG and 'debug_toolbar' in settings.INSTALLED_APPS:
    import debug_toolbar

    urlpatterns.append(path('__debug__/', include(debug_toolbar.urls)))
