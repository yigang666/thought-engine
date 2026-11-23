# Thought Engine

Anyone can read published articles. Uploading an article or a Markdown file requires Google sign-in.

This flow stores the title and the writing and shows them to readers. It does not run thought extraction.

## Run locally

Requires Python 3.11 or newer. This machine can use `python3.12`.

```bash
cd /Users/liyigang/Desktop/cursor-grok/thoughtpage
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
uvicorn app.main:app --host 127.0.0.1 --port 3002
```

Stop any older server first. Open exactly http://localhost:3002 (not 127.0.0.1, and not port 8000). Anyone can read. Sign in with Google sends this redirect URI, unchanged:

```text
http://localhost:3002/auth/google/callback
```

After Google returns, the header shows the account name and email, and Upload appears in the nav. Logged-out pages do not show Upload. Opening /upload while logged out still refuses a post. On an article you published, Edit changes the title and body. Readers see the saved version. Signing out leaves the article readable and closes the editor.

The session secret is created on first run in `data/session-secret`. The Google client used on this machine is in `data/google-oauth.json`. Both are gitignored. Do not commit them. Reading does not require sign-in.

API keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) are unused by this flow.

## Tests

```bash
pytest
```

Covers anonymous reading, a refused anonymous upload, and a signed-in upload that is stored and shown. The Google token exchange is stubbed in tests.
