from django.urls import path

from . import views

urlpatterns = [
    path("health", views.health, name="health"),
    path("resolve", views.resolve, name="resolve"),
    path("presets", views.presets, name="presets"),
]
