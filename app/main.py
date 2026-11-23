"""Public reading, with Google sign-in required to upload an article.

Thought extraction is not part of this flow.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.auth import (
    SIGN_IN_REQUIRED,
    AuthError,
    begin_sign_in,
    current_user,
    finish_sign_in,
    redirect_uri,
    session_secret,
)
from app.reading import article_html
from app.storage import get_article, list_articles, save_article, update_article

MAX_CHARS = 200_000
MAX_TITLE = 200
MAX_UPLOAD_BYTES = 1_048_576
EDIT_SIGN_IN_REQUIRED = "Sign in with Google to edit an article."
APP_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(directory=str(APP_DIR / "templates"))


def create_app() -> FastAPI:
    load_dotenv()
    app = FastAPI(title="Thought Engine", docs_url=None, redoc_url=None)
    app.add_middleware(SessionMiddleware, secret_key=session_secret(), same_site="lax", https_only=False)

    @app.get("/")
    def home(request: Request):
        return render(
            request,
            "index.html",
            {"nav": "articles", "articles": list_articles()},
            indexable=True,
        )

    @app.get("/articles/{article_id}")
    def read_article(request: Request, article_id: str):
        article = get_article(article_id)
        if article is None:
            return missing(request)
        return render(
            request,
            "article.html",
            {"nav": "articles", "article": article, "body_html": article_html(article.content)},
            indexable=True,
        )

    @app.get("/articles/{article_id}/edit")
    def edit_article_form(request: Request, article_id: str):
        if current_user(request) is None:
            return _edit_forbidden(request)
        article = get_article(article_id)
        if article is None:
            return missing(request)
        return _edit_page(request, article)

    @app.post("/articles/{article_id}/edit")
    async def edit_article(request: Request, article_id: str, title: str = Form(""), text: str = Form("")):
        blocked = reject_cross_origin(request)
        if blocked:
            return blocked
        if current_user(request) is None:
            return _edit_forbidden(request)
        article = get_article(article_id)
        if article is None:
            return missing(request)
        try:
            chosen_title, content = await _article_fields(title, text, None)
        except ValueError as exc:
            return _edit_page(request, article, error=str(exc), title_value=title, text_value=text, status_code=400)
        updated = update_article(article_id, title=chosen_title, content=content)
        if updated is None:
            return missing(request)
        return RedirectResponse(f"/articles/{article_id}", status_code=303)

    @app.get("/upload")
    def upload_form(request: Request):
        return _upload_page(request)

    @app.post("/upload")
    async def upload_article(
        request: Request,
        title: str = Form(""),
        text: str = Form(""),
        file: UploadFile | None = File(None),
    ):
        blocked = reject_cross_origin(request)
        if blocked:
            return blocked
        user = current_user(request)
        if user is None:
            return _upload_page(request, error=_anonymous_upload_message(), status_code=403)
        try:
            chosen_title, content = await _article_fields(title, text, file)
        except ValueError as exc:
            return _upload_page(request, error=str(exc), title_value=title, text_value=text, status_code=400)
        article = save_article(
            title=chosen_title,
            content=content,
            author_name=user["name"],
            author_email=user["email"],
        )
        return RedirectResponse(f"/articles/{article.article_id}", status_code=303)

    @app.get("/auth/google")
    def google_start(request: Request):
        try:
            callback = redirect_uri(request)
            if not _same_browser_origin(request, callback):
                target = urlsplit(callback)
                return RedirectResponse(_origin_of(target) + "/auth/google", status_code=302)
            return RedirectResponse(begin_sign_in(request), status_code=302)
        except AuthError as exc:
            return _upload_page(request, error=str(exc))

    @app.get("/auth/google/callback")
    def google_callback(request: Request, code: str = "", state: str = "", error: str = ""):
        if error:
            return _upload_page(request, error="Google sign-in was cancelled.", status_code=403)
        try:
            finish_sign_in(request, code, state)
        except AuthError as exc:
            return _upload_page(request, error=str(exc), status_code=403)
        return RedirectResponse("/upload", status_code=303)

    @app.post("/auth/logout")
    def logout(request: Request):
        blocked = reject_cross_origin(request)
        if blocked:
            return blocked
        request.session.clear()
        return RedirectResponse("/", status_code=303)

    @app.exception_handler(404)
    async def not_found(request: Request, _exc: HTTPException):
        return missing(request)

    app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")
    return app


def load_dotenv() -> None:
    if os.environ.get("THOUGHTPAGE_SKIP_DOTENV") == "1":
        return
    path = APP_DIR.parent / ".env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def render(request: Request, name: str, context: dict, status_code: int = 200, *, indexable: bool = False):
    context["user"] = current_user(request)
    response = templates.TemplateResponse(request, name, context, status_code=status_code)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "same-origin"
    if not indexable:
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


def missing(request: Request):
    return render(
        request,
        "error.html",
        {"nav": "", "message": "That page is not available."},
        status_code=404,
    )


def _upload_page(
    request: Request,
    error: str | None = None,
    title_value: str = "",
    text_value: str = "",
    status_code: int = 200,
):
    return render(
        request,
        "upload.html",
        {
            "nav": "upload",
            "error": error,
            "title_value": title_value,
            "text_value": text_value,
        },
        status_code=status_code,
    )


def _anonymous_upload_message() -> str:
    return SIGN_IN_REQUIRED


def _edit_forbidden(request: Request):
    return render(
        request,
        "error.html",
        {"nav": "articles", "message": EDIT_SIGN_IN_REQUIRED},
        status_code=403,
    )


def _edit_page(
    request: Request,
    article,
    error: str | None = None,
    title_value: str | None = None,
    text_value: str | None = None,
    status_code: int = 200,
):
    return render(
        request,
        "edit.html",
        {
            "nav": "articles",
            "article": article,
            "error": error,
            "title_value": article.title if title_value is None else title_value,
            "text_value": article.content if text_value is None else text_value,
        },
        status_code=status_code,
    )


def _same_browser_origin(request: Request, callback: str) -> bool:
    return _origin_of(urlsplit(str(request.base_url))) == _origin_of(urlsplit(callback))


def _origin_of(parsed) -> str:
    port = parsed.port
    if port is None:
        port = 443 if parsed.scheme == "https" else 80
    default = 443 if parsed.scheme == "https" else 80
    host = parsed.hostname or ""
    if port == default:
        return f"{parsed.scheme}://{host}"
    return f"{parsed.scheme}://{host}:{port}"


async def _article_fields(title: str, text: str, file: UploadFile | None) -> tuple[str, str]:
    pasted = text.strip()
    uploaded = file is not None and bool(file.filename)
    if pasted and uploaded:
        raise ValueError("Paste the article or upload a Markdown file, not both.")
    if uploaded:
        assert file is not None
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in {".md", ".markdown"}:
            raise ValueError("Upload a .md or .markdown file, or paste the article instead.")
        raw = await file.read()
        if len(raw) > MAX_UPLOAD_BYTES:
            raise ValueError("That file is larger than 1 MB.")
        try:
            content = raw.decode("utf-8").strip()
        except UnicodeDecodeError:
            raise ValueError("Markdown files must be UTF-8 text.") from None
        if not title.strip():
            title = Path(file.filename or "").stem
    else:
        content = pasted
    title = " ".join(title.split())
    if not title:
        raise ValueError("Add a title.")
    if len(title) > MAX_TITLE:
        raise ValueError("The title is too long.")
    if not content:
        raise ValueError("Paste an article or choose a Markdown file.")
    if len(content) > MAX_CHARS:
        raise ValueError("That article is longer than 200,000 characters.")
    return title, content


_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


def reject_cross_origin(request: Request):
    """Block a browser post from another site.

    Compare the Origin the browser sends with the Host it addressed. Loopback
    names are the same machine, and a local proxy may rewrite only the scheme
    through X-Forwarded-Proto, so that rewrite must not fail a local form.
    """
    origin = (request.headers.get("origin") or "").strip()
    if not origin:
        return None
    if origin == "null" and request.headers.get("sec-fetch-site") == "same-origin":
        return None
    parsed = urlsplit(origin)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return _cross_origin_denied(request)
    origin_port = parsed.port or (443 if parsed.scheme == "https" else 80)
    request_host, request_port = _request_host_port(request)
    if not _same_site(parsed.hostname, origin_port, request_host, request_port):
        return _cross_origin_denied(request)
    if parsed.scheme != (request.url.scheme or "http") and not _loopback(parsed.hostname):
        return _cross_origin_denied(request)
    return None


def _cross_origin_denied(request: Request):
    return render(
        request,
        "error.html",
        {"nav": "", "message": "This form only accepts posts from this site."},
        status_code=403,
    )


def _request_host_port(request: Request) -> tuple[str, int]:
    raw = (request.headers.get("host") or "").strip()
    if raw:
        parsed = urlsplit(f"//{raw}")
        host = parsed.hostname or ""
        if parsed.port is not None:
            return host, parsed.port
        default = 443 if (request.url.scheme or "http") == "https" else 80
        return host, default
    host = request.url.hostname or ""
    port = request.url.port or (443 if request.url.scheme == "https" else 80)
    return host, port


def _loopback(host: str) -> bool:
    return host.lower().strip("[]").rstrip(".") in _LOOPBACK_HOSTS


def _same_site(origin_host: str, origin_port: int, request_host: str, request_port: int) -> bool:
    if origin_port != request_port or not origin_host or not request_host:
        return False
    left = origin_host.lower().strip("[]").rstrip(".")
    right = request_host.lower().strip("[]").rstrip(".")
    if left == right:
        return True
    return _loopback(left) and _loopback(right)


app = create_app()
