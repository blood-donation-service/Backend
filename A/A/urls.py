from django.contrib import admin
from django.urls import path, include
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('accounts.urls')),
    path('', include('home.urls')),
]

if 'debug_toolbar' in settings.INSTALLED_APPS:
    urlpatterns += [
        path('__debug__/', include('debug_toolbar.urls')),
    ]
