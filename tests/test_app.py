import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient

from app.main import create_app


def test_anonymous_reader_can_open_the_site_and_cannot_upload(client):
    home = client.get("/")
    assert home.status_code == 200
    assert "No articles yet." in home.text
    assert "Thought Map" not in home.text
    assert 'href="/auth/google"' in home.text
    assert "Sign in with Google" in home.text
    assert 'href="/upload"' not in home.text
    assert "GOOGLE_CLIENT_ID" not in home.text
    assert "GOOGLE_CLIENT_SECRET" not in home.text
    assert "SESSION_SECRET" not in home.text
    assert "Sign out" not in home.text

    explained = client.get("/auth/google")
    assert explained.status_code == 200
    assert "not available" in explained.text
    assert "GOOGLE_CLIENT_ID" not in explained.text
    assert "location" not in explained.headers

    upload = client.get("/upload")
    assert upload.status_code == 200
    assert "Sign in with Google" in upload.text
    assert 'href="/upload"' not in upload.text
    assert "GOOGLE_CLIENT_ID" not in upload.text
    assert 'action="/upload"' not in upload.text

    pasted = client.post(
        "/upload",
        data={"title": "Secret draft", "text": "This must not be published."},
    )
    assert pasted.status_code == 403
    assert "Secret draft" not in pasted.text
    filed = client.post(
        "/upload",
        data={"title": "Secret file"},
        files={"file": ("note.md", b"Hidden markdown.", "text/markdown")},
    )
    assert filed.status_code == 403
    assert "Secret file" not in client.get("/").text
    assert "Hidden markdown." not in client.get("/").text
    assert "This must not be published." not in client.get("/").text


def test_signed_in_upload_is_stored_and_readable_without_login(client, monkeypatch):
    def explode(*_args, **_kwargs):
        raise AssertionError("thought extraction ran")

    monkeypatch.setattr("app.extraction.extract_thought_map", explode)
    author = TestClient(create_app(), follow_redirects=False)
    _sign_in(author, monkeypatch)

    published = author.post(
        "/upload",
        data={
            "title": "Public note",
            "text": "Hello readers.\n\n## Kept\n\nA visible paragraph.\n\n<script>alert(1)</script>",
        },
    )
    assert published.status_code == 303, published.text
    location = published.headers["location"]
    assert location.startswith("/articles/")

    page = client.get(location)
    assert page.status_code == 200
    assert 'class="reading"' in page.text
    assert 'class="article-body"' in page.text
    assert "<h1>Public note</h1>" in page.text
    assert "Ada Lovelace" in page.text
    assert "Hello readers." in page.text
    assert "<p>A visible paragraph.</p>" in page.text
    assert "<h2>Kept</h2>" in page.text
    assert "A visible paragraph." in page.text
    assert 'href="/upload"' not in page.text
    assert "<script>" not in page.text
    assert "alert(1)" in page.text
    assert "Thought Map" not in page.text

    home = client.get("/")
    assert "Public note" in home.text
    assert home.status_code == 200


def test_signed_in_markdown_file_is_displayed(client, monkeypatch):
    author = TestClient(create_app(), follow_redirects=False)
    _sign_in(author, monkeypatch, email="editor@gmail.com", name="Editor")
    published = author.post(
        "/upload",
        data={"title": "From a file"},
        files={"file": ("note.md", b"# Ignored as a title\n\nA paragraph from markdown.\n", "text/markdown")},
    )
    assert published.status_code == 303, published.text
    page = client.get(published.headers["location"])
    assert page.status_code == 200
    assert "From a file" in page.text
    assert "A paragraph from markdown." in page.text
    assert "Editor" in page.text


def test_signed_in_edit_is_what_readers_see(client, monkeypatch):
    def explode(*_args, **_kwargs):
        raise AssertionError("thought extraction ran")

    monkeypatch.setattr("app.extraction.extract_thought_map", explode)
    author = TestClient(create_app(), follow_redirects=False)
    _sign_in(author, monkeypatch)
    published = author.post(
        "/upload",
        data={"title": "Original title", "text": "Original body that readers saw first."},
    )
    assert published.status_code == 303, published.text
    url = published.headers["location"]
    editor = author.get(f"{url}/edit")
    assert editor.status_code == 200
    assert "Original title" in editor.text
    assert "Original body that readers saw first." in editor.text
    assert f'action="{url}/edit"' in editor.text
    saved = author.post(
        f"{url}/edit",
        data={"title": "Revised title", "text": "Revised body.\n\n## After\n\nVisible to readers."},
    )
    assert saved.status_code == 303, saved.text
    assert saved.headers["location"] == url
    page = client.get(url)
    assert page.status_code == 200
    assert "<h1>Revised title</h1>" in page.text
    assert "Revised body." in page.text
    assert "<h2>After</h2>" in page.text
    assert "Original body that readers saw first." not in page.text
    assert "Original title" not in client.get("/").text
    assert "Revised title" in client.get("/").text
    assert 'href="' + url + '/edit"' in author.get(url).text
    assert 'href="' + url + '/edit"' not in page.text


def test_published_article_uses_reading_typography(client):
    css = client.get("/static/style.css")
    assert css.status_code == 200
    sheet = css.text
    assert ".reading {" in sheet
    reading = sheet.split(".reading {", 1)[1].split("}", 1)[0]
    assert "max-width: none;" in reading
    assert "margin: 0;" in reading
    assert "auto" not in reading
    assert "width: min(64rem, calc(100% - clamp(1.25rem, 4vw, 6rem)));" in sheet
    assert "font-size: 1.5rem;" in sheet
    assert "40rem" not in sheet
    assert "scrollbar-gutter: stable;" in sheet
    assert "view-transition-name: site-header;" in sheet
    assert "view-transition-name: reading-column;" in sheet
    assert "min-height: 2.75rem;" in sheet
    assert ".reading h1 {" in sheet
    assert "font-size: 2.6rem;" in sheet
    assert "line-height: 1.2;" in sheet
    assert ".reading .article-body {" in sheet
    assert "font-size: 1.25rem;" in sheet
    assert "line-height: 1.75;" in sheet
    assert ".reading .article-body h2 {" in sheet
    assert "font-size: 1.7rem;" in sheet
    assert ".reading .article-body h3 {" in sheet
    assert "font-size: 1.35rem;" in sheet
    assert ".reading .article-body p {" in sheet
    assert "margin: 0 0 1.5em;" in sheet


def test_another_signed_in_user_cannot_edit_the_article(client, monkeypatch):
    from app.storage import get_user

    ada = TestClient(create_app(), follow_redirects=False)
    _sign_in(ada, monkeypatch, email="ada@gmail.com", name="Ada Lovelace")
    published = ada.post(
        "/upload",
        data={"title": "Ada note", "text": "Written by Ada."},
    )
    assert published.status_code == 303, published.text
    url = published.headers["location"]
    stored = get_user("sub-ada@gmail.com")
    assert stored is not None
    assert stored.email == "ada@gmail.com"
    assert stored.name == "Ada Lovelace"
    grace = TestClient(create_app(), follow_redirects=False)
    _sign_in(grace, monkeypatch, email="grace@gmail.com", name="Grace Hopper")
    assert get_user("sub-grace@gmail.com") is not None
    opened = grace.get(f"{url}/edit")
    assert opened.status_code == 403
    assert "Only the author can edit" in opened.text
    assert 'name="text"' not in opened.text
    assert "Written by Ada." not in opened.text
    posted = grace.post(f"{url}/edit", data={"title": "Grace takes it", "text": "This is not Ada's."})
    assert posted.status_code == 403
    page = client.get(url)
    assert page.status_code == 200
    assert "Ada note" in page.text
    assert "Written by Ada." in page.text
    assert "Grace takes it" not in page.text
    assert 'href="' + url + '/edit"' not in grace.get(url).text
    assert 'href="' + url + '/edit"' in ada.get(url).text
    saved = ada.post(f"{url}/edit", data={"title": "Ada revises", "text": "Still written by Ada."})
    assert saved.status_code == 303, saved.text
    assert "Ada revises" in client.get(url).text
    assert "Still written by Ada." in client.get(url).text


def test_anonymous_cannot_open_or_submit_the_editor(client, monkeypatch):
    author = TestClient(create_app(), follow_redirects=False)
    _sign_in(author, monkeypatch)
    published = author.post(
        "/upload",
        data={"title": "Stay public", "text": "Leave this body alone."},
    )
    url = published.headers["location"]
    opened = client.get(f"{url}/edit")
    assert opened.status_code == 403
    assert "Sign in with Google to edit" in opened.text
    assert 'name="text"' not in opened.text
    assert "Leave this body alone." not in opened.text
    posted = client.post(f"{url}/edit", data={"title": "Hijack", "text": "Stolen."})
    assert posted.status_code == 403
    page = client.get(url)
    assert page.status_code == 200
    assert "Stay public" in page.text
    assert "Leave this body alone." in page.text
    assert "Hijack" not in page.text
    assert "Stolen." not in page.text


def test_configured_google_sends_anonymous_visitors_to_sign_in(client, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "client-secret")
    home = client.get("/")
    assert home.status_code == 200
    assert 'href="/auth/google"' in home.text
    assert "Sign in with Google" in home.text
    assert "not configured" not in home.text
    assert "SESSION_SECRET" not in home.text
    start = client.get("/auth/google")
    assert start.status_code == 302
    assert start.headers["location"].startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert parse_qs(urlsplit(start.headers["location"]).query)["client_id"] == ["client-id"]
    page = client.get("/upload")
    assert page.status_code == 200
    assert "Sign in with Google" in page.text
    assert "not configured" not in page.text
    refused = client.post("/upload", data={"title": "Nope", "text": "Still private."})
    assert refused.status_code == 403
    assert "Sign in with Google" in refused.text
    assert "Nope" not in client.get("/").text
    assert client.get("/").status_code == 200


def test_other_sites_cannot_publish(client, monkeypatch):
    author = TestClient(create_app(), base_url="http://127.0.0.1:8000", follow_redirects=False)
    _sign_in(author, monkeypatch)
    refused = author.post(
        "/upload",
        data={"title": "Cross site", "text": "Should stay unpublished."},
        headers={"origin": "https://evil.example"},
    )
    assert refused.status_code == 403
    assert "this site" in refused.text
    assert "Cross site" not in client.get("/").text


def test_signed_in_header_shows_the_account_and_sign_out(client, monkeypatch):
    author = TestClient(create_app(), follow_redirects=False)
    _sign_in(author, monkeypatch)
    page = author.get("/")
    assert page.status_code == 200
    assert "Ada Lovelace" in page.text
    assert "ada@gmail.com" in page.text
    assert "Sign out" in page.text
    assert 'href="/auth/google"' not in page.text
    assert 'href="/upload"' in page.text
    article = author.get("/upload")
    assert 'action="/upload"' in article.text
    assert 'href="/upload"' in article.text
    left = author.post("/auth/logout")
    assert left.status_code == 303
    assert left.headers["location"] == "/"
    home = author.get("/")
    assert "Sign in with Google" in home.text
    assert "ada@gmail.com" not in home.text
    assert 'href="/upload"' not in home.text


def test_session_secret_is_persisted_without_asking(data_dir, monkeypatch):
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "client-secret")
    from app.auth import session_secret

    first = session_secret()
    assert first == (data_dir / "session-secret").read_text(encoding="utf-8").strip()
    assert session_secret() == first
    reader = TestClient(create_app(), follow_redirects=False)
    home = reader.get("/")
    assert home.status_code == 200
    assert "No articles yet." in home.text
    assert "SESSION_SECRET" not in home.text
    assert "GOOGLE_CLIENT_ID" not in home.text
    start = reader.get("/auth/google")
    assert start.status_code == 302
    assert start.headers["location"].startswith("https://accounts.google.com/o/oauth2/v2/auth?")


def test_auth_url_uses_the_registered_redirect_exactly(data_dir, monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://127.0.0.1:8000/auth/google/callback")
    registered = "http://localhost:3002/auth/google/callback"
    (data_dir / "google-oauth.json").write_text(
        json.dumps(
            {
                "client_id": "local-client",
                "client_secret": "local-secret",
                "redirect_uri": registered,
            }
        ),
        encoding="utf-8",
    )
    wrong = TestClient(create_app(), base_url="http://127.0.0.1:8000", follow_redirects=False)
    hop = wrong.get("/auth/google")
    assert hop.status_code == 302
    assert hop.headers["location"] == "http://localhost:3002/auth/google"
    assert "local-secret" not in hop.headers["location"]
    right = TestClient(create_app(), base_url="http://localhost:3002", follow_redirects=False)
    start = right.get("/auth/google")
    location = start.headers["location"]
    assert start.status_code == 302
    assert location.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    query = parse_qs(urlsplit(location).query)
    assert query["client_id"] == ["local-client"]
    assert query["redirect_uri"] == [registered]
    assert query["redirect_uri"] == ["http://localhost:3002/auth/google/callback"]
    assert "127.0.0.1:8000" not in location
    assert "local-secret" not in location


def test_env_example_does_not_ask_for_google_secrets():
    root = Path(__file__).resolve().parents[1]
    example = (root / ".env.example").read_text(encoding="utf-8")
    assert "GOOGLE_CLIENT_SECRET=" not in example
    assert "SESSION_SECRET=" not in example
    ignore = (root / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in ignore
    assert "data/*" in ignore


def _sign_in(client, monkeypatch, email="ada@gmail.com", name="Ada Lovelace"):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "client-secret")

    def identity(code, redirect_to):
        assert code == "good-code"
        assert redirect_to.endswith("/auth/google/callback")
        return {"email": email, "name": name, "sub": "sub-" + email}

    monkeypatch.setattr("app.auth.fetch_google_identity", identity)
    start = client.get("/auth/google")
    assert start.status_code == 302, start.text
    state = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]
    done = client.get("/auth/google/callback", params={"code": "good-code", "state": state})
    assert done.status_code == 303, done.text
    assert done.headers["location"] == "/upload"
