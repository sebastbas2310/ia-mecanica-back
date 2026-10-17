"""Diagnóstico de conexión con Supabase. Uso: uv run python scripts/diagnose_supabase.py

Prueba paso a paso: configuración -> DNS -> HTTPS -> Auth API -> JWKS.
No imprime las claves completas.
"""
import socket
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402

from app.config import settings  # noqa: E402


def step(name: str, ok: bool, detail: str = "") -> None:
    print(f"[{'OK ' if ok else 'ERR'}] {name}" + (f" -> {detail}" if detail else ""))


url = settings.supabase_url
key = settings.supabase_anon_key
step("SUPABASE_URL", bool(url) and "TU-PROYECTO" not in url, url)
step("SUPABASE_ANON_KEY", bool(key) and not key.startswith("tu-"), f"{key[:15]}… (len {len(key)})")

host = urlparse(url).hostname or ""
try:
    ip = socket.gethostbyname(host)
    step("DNS", True, f"{host} -> {ip}")
except OSError as e:
    step("DNS", False, f"{type(e).__name__}: {e}")
    sys.exit(1)

checks = [
    ("Auth health", f"{url}/auth/v1/health", {"apikey": key}),
    ("Auth settings", f"{url}/auth/v1/settings", {"apikey": key}),
    ("JWKS", settings.jwks_url, {}),
]
for name, u, headers in checks:
    try:
        r = httpx.get(u, headers=headers, timeout=15)
        step(name, r.status_code < 400, f"HTTP {r.status_code} {r.text[:160]!r}")
    except httpx.HTTPError as e:
        step(name, False, f"{type(e).__name__}: {e!r}")
