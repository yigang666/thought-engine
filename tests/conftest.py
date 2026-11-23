import os

os.environ["THOUGHTPAGE_SKIP_DOTENV"] = "1"
for _name in (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "LLM_PROVIDER",
    "OPENAI_BASE_URL",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "GOOGLE_REDIRECT_URI",
    "SESSION_SECRET",
):
    os.environ.pop(_name, None)

import pytest


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("THOUGHTPAGE_DATA_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture()
def client(data_dir, monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret")
    from fastapi.testclient import TestClient

    from app.main import create_app

    return TestClient(create_app(), follow_redirects=False)
