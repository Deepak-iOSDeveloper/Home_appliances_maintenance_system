"""
ARHIS — URL Configuration
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # API v1
    path('api/dashboard/', include('apps.dashboard.urls')),
    path('api/diagnostics/', include('apps.diagnostics.urls')),
    path('api/troubleshooter/', include('apps.troubleshooter.urls')),
    path('api/observability/', include('apps.observability.urls')),
]
