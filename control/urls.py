from django.urls import path

from . import views

urlpatterns = [
    path('control/', views.control_device, name='control-device'),
    path('control/health/', views.control_health, name='control-health'),
]
