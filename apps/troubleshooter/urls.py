"""Troubleshooter URL Configuration"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'manuals', views.TechnicalManualViewSet, basename='manual')
router.register(r'sessions', views.ChatSessionViewSet, basename='session')

urlpatterns = [
    path('', include(router.urls)),
]
