# everpack_system/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

def redirect_to_dashboard(request):
    return redirect('dashboard:home')

def redirect_to_admin(request):
    """Redirect old admin URL to new Admin URL"""
    return redirect('/Admin/')

urlpatterns = [
    path('Admin/', admin.site.urls),
    path('admin/', redirect_to_admin, name='admin_redirect'),
    path('', redirect_to_dashboard, name='home'),
    path('dashboard/', include('dashboard.urls')),
    path('inventory/', include('inventory.urls')),
    path('sales/', include('sales.urls')),
    path('reports/', include('reports.urls')),
    path('accounts/', include('accounts.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)