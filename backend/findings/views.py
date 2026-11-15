import hashlib
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Finding
from .serializers import FindingSerializer

RATE_LIMIT_PER_HOUR = 5


def _get_client_ip_hash(request) -> str:
    num_proxies = getattr(settings, "NUM_PROXIES", 0)
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if num_proxies > 0 and forwarded:
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        # Pick the client IP appended by our trusted reverse proxy, not the spoofable left-most header
        idx = max(0, len(parts) - num_proxies)
        ip = parts[idx] if parts else request.META.get("REMOTE_ADDR", "unknown")
    else:
        ip = request.META.get("REMOTE_ADDR", "unknown")
    payload = f"{settings.SECRET_KEY}:{ip}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@api_view(["GET", "POST"])
def findings_list_create(request):
    """List recent community findings or submit a new candidate with spam protection."""
    if request.method == "GET":
        recent = Finding.objects.all()[:50]
        serializer = FindingSerializer(recent, many=True)
        return Response(serializer.data)

    # Honeypot anti-spam field: bots filling hidden "website" field are rejected
    honeypot = str(request.data.get("website", "") or "").strip()
    if honeypot:
        return Response(
            {"code": "invalid_submission", "detail": "Submission rejected."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    ip_hash = _get_client_ip_hash(request)
    one_hour_ago = timezone.now() - timedelta(hours=1)
    recent_count = Finding.objects.filter(
        ip_hash=ip_hash,
        created_at__gte=one_hour_ago,
    ).count()
    if recent_count >= RATE_LIMIT_PER_HOUR:
        return Response(
            {
                "code": "rate_limited",
                "detail": "Rate limit exceeded (max 5 findings per hour).",
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    serializer = FindingSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"code": "validation_error", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    finding = serializer.save(ip_hash=ip_hash)
    return Response(FindingSerializer(finding).data, status=status.HTTP_201_CREATED)
