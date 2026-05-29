from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('app_foto_config.app_urls')),
    path('accounts/', include('django.contrib.auth.urls')),  # Добавьте эту строку
    # Изменяем путь для логина
    path('login/', auth_views.LoginView.as_view(
        template_name='login.html',
        redirect_authenticated_user=True  # Перенаправлять уже авторизованных
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]