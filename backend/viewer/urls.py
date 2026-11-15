"""Viewer routes, mounted under /api/ (COMMON §6)."""
from django.urls import path, re_path

from . import views

urlpatterns = [
    path("blink", views.blink_view),
    re_path(r"^blink/status/(?P<job_id>[0-9a-f]{32})$", views.status_view),
    re_path(r"^frame/(?P<fid>[0-9a-f]{1,64})\.png$", views.frame_view),
]
