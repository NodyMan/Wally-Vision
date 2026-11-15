"""Science routes, mounted under /api/ (COMMON §6)."""
from django.urls import path

from . import views

urlpatterns = [
    path("catalog", views.catalog_view),
    path("spectrum", views.spectrum_view),
    path("lightcurve", views.lightcurve_view),
]
