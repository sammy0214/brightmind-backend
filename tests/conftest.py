import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp}/test.db"
os.environ["STORAGE_DIR"] = f"{_tmp}/data"
os.environ["ANTHROPIC_API_KEY"] = ""  # force offline dev tutor
os.environ["JWT_SECRET"] = "test-secret"
os.environ["REGION"] = "africa"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:  # runs lifespan -> creates tables
        yield c


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
