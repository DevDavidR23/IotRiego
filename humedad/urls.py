from django.urls import path

from . import views

urlpatterns = [
    path('humedad/', views.humedad_list, name='humedad-list'),
    path('humedad/<int:pk>/', views.humedad_detail, name='humedad-detail'),
]
