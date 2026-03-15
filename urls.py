"""
taxi_project/urls.py
Root URL configuration.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Django admin
    path("admin/", admin.site.urls),
    # All taxiapp views + API
    path("", include("taxiapp.urls")),
    # Browsable DRF login (dev only)
    path("api-auth/", include("rest_framework.urls")),
]

# Serve uploaded media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
