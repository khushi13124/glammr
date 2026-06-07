"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render
from django.shortcuts import redirect
from accounts.views import index_view 

def auth_page(request):
    return render(request, 'auth.html')

def spa_home(request):
    return render(request, 'index.html')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda request: redirect('auth/', permanent=False)),
    path('', spa_home),   # Route homepage to index.html
    path('', include('api.urls')),
    path('', include('accounts.urls')),   
    path('auth/', include('accounts.urls')),     # For login/signup
    path('index/', index_view, name='index'),
    ]

# Serve static and media files during development
if settings.DEBUG:
    # Serve user uploaded files
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Serve DeepFashion dataset images
    urlpatterns += static(settings.DEEPFASHION_IMAGE_URL, document_root=settings.DEEPFASHION_IMAGE_ROOT)
    
    # Serve static files (CSS, JS)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])