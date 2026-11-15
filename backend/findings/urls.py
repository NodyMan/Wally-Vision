from django.urls import path

from . import views

urlpatterns = [
    path("findings", views.findings_list_create, name="findings"),
]
