from django.contrib import admin
from django.urls import path, include
from django.conf import settings 
from django.conf.urls.static import static 
from appointment import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.login_request, name='login'),
    path('register/', auth_views.register_request, name='register'),
    path('logout/', auth_views.logout_request, name='logout'),
    path('', include('main.urls')),
    path('auth/', include('appointment.urls')),   
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
