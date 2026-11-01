from __future__ import annotations

import logging

from app.core.config import settings


def setup_logging() -> None:
    logging.basicConfig(
        level=settings.LOG_LEVEL.upper(),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


logger = logging.getLogger("app")
