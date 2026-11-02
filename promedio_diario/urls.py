from django.urls import path

from . import views

urlpatterns = [
    path('promedio-diario/', views.promedio_diario_list, name='promedio-diario-list'),
    path('promedio-diario/<int:pk>/', views.promedio_diario_detail, name='promedio-diario-detail'),
]
