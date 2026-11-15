from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

def root(request):
    """Plain landing answer so the bare API URL is not a 404."""
    return JsonResponse({"service": "skyblink-api", "health": "/api/health", "site": "https://frontend-three-xi-80.vercel.app"})


urlpatterns = [
    path("", root),
    path("admin/", admin.site.urls),
    path("api/", include("platform_api.urls")),
    path("api/", include("findings.urls")),
    path("api/", include("viewer.urls")),    # #1: blink, blink/status, frame
    path("api/", include("science.urls")),   # #2: catalog, spectrum, lightcurve
]
