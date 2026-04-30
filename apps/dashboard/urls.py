"""Dashboard URL Configuration"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'homes', views.HomeViewSet, basename='home')
router.register(r'rooms', views.RoomViewSet, basename='room')
router.register(r'devices', views.DeviceViewSet, basename='device')
router.register(r'health-score', views.HealthScoreViewSet, basename='health-score')

urlpatterns = [
    path('', include(router.urls)),
]
