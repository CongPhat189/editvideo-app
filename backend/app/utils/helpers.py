from __future__ import annotations

import time


def normalize_platforms(platforms: list[str] | None) -> list[str]:
    items = platforms or []
    return list(dict.fromkeys(str(item).lower() for item in items))


def new_id() -> int:
    return time.time_ns() // 1_000_000
