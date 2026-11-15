from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .presets import load_presets
from .resolver import ResolveError, resolve_target


@api_view(["GET"])
def health(request):
    """Lightweight liveness check used by frontend wake-up ping and Render healthchecks."""
    return Response({"status": "ok"})


@api_view(["GET"])
def resolve(request):
    """Resolve an object name (via CDS Sesame) or coordinate string into ICRS RA/Dec."""
    query = request.query_params.get("q", "")
    try:
        target = resolve_target(query)
    except ResolveError as exc:
        return Response(
            {"code": exc.code, "detail": str(exc)},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(target.to_dict())


@api_view(["GET"])
def presets(request):
    """Return the curated list of 5 mandatory SkyBlink benchmark targets."""
    return Response(load_presets())
