from __future__ import annotations

import json
import urllib.request
from typing import Any


def request_json(method: str, url: str, payload: dict[str, Any] | None = None, headers: dict[str, str] | None = None, timeout: int = 30) -> dict[str, Any]:
    """Gọi 1 API JSON bên ngoài (dùng thư viện chuẩn, không cần cài thêm)."""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method.upper())
    req.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body) if body else {}
