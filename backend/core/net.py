"""
HTTP к IRSA: правильные сертификаты (Windows + антивирусы), таймауты.
Developed with SI assistance (Claude); reviewed by team #1.
"""
from __future__ import annotations

import ssl
import urllib.request

from . import config


def ssl_context() -> ssl.SSLContext:
    """Сертификаты ОС (truststore) → certifi → стандарт. Проверку SSL никогда не отключаем."""
    try:
        import truststore
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:
        pass
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def urlopen(url: str, timeout: float = config.HTTP_TIMEOUT):
    if not url.startswith(config.IRSA):  # бэкенд ходит только в IRSA — не открытый прокси
        raise ValueError("untrusted_url")
    return urllib.request.urlopen(url, timeout=timeout, context=ssl_context())
