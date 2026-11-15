"""Helpers for serving shared/presets.json."""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings


def load_presets() -> list[dict]:
    presets_path = Path(settings.SHARED_DIR) / "presets.json"
    return json.loads(presets_path.read_text(encoding="utf-8"))
