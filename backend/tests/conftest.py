import os
import tempfile
from pathlib import Path

import pytest

# Dùng DB tạm khi test, không đụng vào connector_screen.db thật
_tmp = Path(tempfile.mkdtemp()) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.as_posix()}"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c
