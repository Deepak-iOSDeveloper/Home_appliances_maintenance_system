"""Diagnostics URL Configuration"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'nodes', views.MatterNodeViewSet, basename='matter-node')

urlpatterns = [
    path('', include(router.urls)),
    path(
        'logs/<uuid:node_pk>/',
        views.DiagnosticLogViewSet.as_view({'get': 'list'}),
        name='node-logs',
    ),
]
