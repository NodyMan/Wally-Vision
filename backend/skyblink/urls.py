from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("platform_api.urls")),
    path("api/", include("findings.urls")),
    path("api/", include("viewer.urls")),    # #1: blink, blink/status, frame
    path("api/", include("science.urls")),   # #2: catalog, spectrum, lightcurve
]
