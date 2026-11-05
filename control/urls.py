from django.urls import path

from . import views

urlpatterns = [
    path('control/', views.control_device, name='control-device'),
    path('control/motor/', views.control_motor, name='control-motor'),
    path('control/read-sensor/', views.control_read_sensor, name='control-read-sensor'),
    path('control/health/', views.control_health, name='control-health'),
]
