"""SkyBlink Platform CLI for checking health, resolving targets, and listing presets."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent


def _setup_django() -> None:
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "skyblink.settings")
    import django

    django.setup()


def cmd_health(args: argparse.Namespace) -> int:
    if args.api:
        import requests

        url = f"{args.api.rstrip('/')}/api/health"
        resp = requests.get(url, timeout=10)
        print(f"GET {url} -> {resp.status_code}")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
        return 0 if resp.ok else 1

    _setup_django()
    from django.test import Client

    client = Client(HTTP_HOST="localhost")
    resp = client.get("/api/health")
    print(f"LOCAL GET /api/health -> {resp.status_code}")
    print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    return 0 if resp.status_code == 200 else 1


def cmd_resolve(args: argparse.Namespace) -> int:
    query = " ".join(args.query).strip()
    if not query:
        print("Error: provide an object name or coordinate string.")
        return 2
    if args.api:
        import requests

        url = f"{args.api.rstrip('/')}/api/resolve"
        resp = requests.get(url, params={"q": query}, timeout=15)
        print(f"GET {url}?q={query} -> {resp.status_code}")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
        return 0 if resp.ok else 1

    _setup_django()
    from platform_api.resolver import ResolveError, resolve_target

    try:
        target = resolve_target(query)
        print(json.dumps(target.to_dict(), indent=2, ensure_ascii=False))
        return 0
    except ResolveError as exc:
        print(json.dumps({"code": exc.code, "detail": str(exc)}, indent=2, ensure_ascii=False))
        return 1


def cmd_presets(args: argparse.Namespace) -> int:
    if args.api:
        import requests

        url = f"{args.api.rstrip('/')}/api/presets"
        resp = requests.get(url, timeout=10)
        data = resp.json()
    else:
        _setup_django()
        from platform_api.presets import load_presets

        data = load_presets()

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0

    lang = args.lang
    for item in data:
        title = item["title"].get(lang) or item["title"]["en"]
        short = item["short"].get(lang) or item["short"]["en"]
        print(f"- [{item['slug']}] {title} ({item['ra']}, {item['dec']}) mode={item['default_mode']}")
        print(f"  {short}")
    return 0


def cmd_findings(args: argparse.Namespace) -> int:
    if args.api:
        import requests

        url = f"{args.api.rstrip('/')}/api/findings"
        if args.add:
            resp = requests.post(
                url,
                json={
                    "ra": args.ra,
                    "dec": args.dec,
                    "note": args.note,
                    "nickname": args.nickname,
                    "website": "",
                },
                timeout=10,
            )
        else:
            resp = requests.get(url, timeout=10)
        print(f"{'POST' if args.add else 'GET'} {url} -> {resp.status_code}")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
        return 0 if resp.ok else 1

    _setup_django()
    from django.test import Client

    client = Client(HTTP_HOST="localhost")
    if args.add:
        resp = client.post(
            "/api/findings",
            data={
                "ra": args.ra,
                "dec": args.dec,
                "note": args.note,
                "nickname": args.nickname,
                "website": "",
            },
            content_type="application/json",
        )
    else:
        resp = client.get("/api/findings")
    print(f"LOCAL {'POST' if args.add else 'GET'} /api/findings -> {resp.status_code}")
    print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    return 0 if resp.status_code in (200, 201) else 1


def cmd_check(_args: argparse.Namespace) -> int:
    steps = [
        ("Django system check", [sys.executable, "manage.py", "check"], BACKEND_DIR),
        ("Backend pytest", [sys.executable, "-m", "pytest"], BACKEND_DIR),
        ("i18n check", ["node", str(ROOT_DIR / "scripts" / "check_i18n.mjs")], ROOT_DIR),
    ]
    for label, cmd, cwd in steps:
        print(f"\n=== {label} ===")
        res = subprocess.run(cmd, cwd=str(cwd))
        if res.returncode != 0:
            print(f"[FAIL] {label}")
            return res.returncode
    print("\nAll checks passed!")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skyblink-cli",
        description="CLI for SkyBlink platform checks, target resolution, and presets.",
    )
    parser.add_argument(
        "--api",
        help="Optional running backend base URL (e.g. http://localhost:8000). Uses in-process Django if omitted.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_health = sub.add_parser("health", help="Check /api/health endpoint")
    p_health.set_defaults(func=cmd_health)

    p_resolve = sub.add_parser("resolve", help="Resolve an object name or RA/Dec coordinates")
    p_resolve.add_argument(
        "query",
        nargs=argparse.REMAINDER,
        help="Object name or coordinates (supports negative values without --)",
    )
    p_resolve.set_defaults(func=cmd_resolve)

    p_presets = sub.add_parser("presets", help="List the 5 SkyBlink benchmark presets")
    p_presets.add_argument("--lang", choices=["en", "ru", "uz"], default="en")
    p_presets.add_argument("--json", action="store_true", help="Output raw JSON")
    p_presets.set_defaults(func=cmd_presets)

    p_check = sub.add_parser("check", help="Run Django check, pytest, and i18n check")
    p_check.set_defaults(func=cmd_check)

    p_findings = sub.add_parser("findings", help="List or submit community findings")
    p_findings.add_argument("--add", action="store_true", help="Submit a new finding")
    p_findings.add_argument("--ra", type=float, default=133.795129)
    p_findings.add_argument("--dec", type=float, default=-7.245147)
    p_findings.add_argument("--note", default="CLI test finding")
    p_findings.add_argument("--nickname", default="CLI")
    p_findings.set_defaults(func=cmd_findings)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
