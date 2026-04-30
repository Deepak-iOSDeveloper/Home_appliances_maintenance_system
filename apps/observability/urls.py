"""Observability URL Configuration"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'traces', views.ThoughtTraceViewSet, basename='thought-trace')
router.register(r'metrics', views.SessionMetricViewSet, basename='session-metric')

urlpatterns = [
    path('', include(router.urls)),
]
