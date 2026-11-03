# Quizly Backend

REST API for Quizly. It turns a YouTube video into a quiz with ten
questions: the audio is downloaded with yt-dlp, transcribed locally
with Whisper and turned into questions by Gemini. Built with Django and
Django REST Framework.

## Requirements

- Python 3.14
- FFmpeg, installed globally and available on the PATH (Whisper needs it)
  - Windows: `winget install --id Gyan.FFmpeg -e --source winget`
  - macOS: `brew install ffmpeg`
- A free Gemini API key from https://aistudio.google.com/apikey

## Setup

```bash
git clone <repository-url>
cd quizly_Backend
python -m venv venv
venv\Scripts\activate          # macOS / Linux: source venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in both values. A secret key can
be generated with:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Then set up the database and start the server:

```bash
python manage.py migrate
python manage.py runserver
```

The API runs at `http://127.0.0.1:8000/api/`.

## Notes

- Open the frontend via `http://127.0.0.1:5500`, not `localhost`. The
  auth cookies are only sent when frontend and backend use the same
  host.
- Authentication uses JWT in HttpOnly cookies (`access_token`,
  `refresh_token`). The access token is valid for 5 minutes, the
  refresh token for one day. Logout blacklists the refresh token.
- The cookies are not marked `secure` because the project runs on plain
  HTTP locally. Enable it when serving over HTTPS.
- Creating a quiz runs synchronously and can take a few minutes. The
  first run also downloads the Whisper `base` model (about 140 MB).
- Only YouTube URLs are accepted. Audio files are stored in a temporary
  folder and deleted afterwards.
- yt-dlp may warn that no JavaScript runtime was found. Downloads still
  work; if YouTube downloads start failing, install
  [Deno](https://deno.com/).
- Error responses are kept short: every failed download returns
  `400 {"detail": "Video could not be downloaded."}`, every failed quiz
  generation returns `500 {"detail": "Quiz generation failed."}`. The
  limits below explain the most common reasons.
- `DEBUG` is enabled and `ALLOWED_HOSTS` is empty; the settings are
  meant for local development only.
- The project's own test suite is not part of this repository.

## Limits and settings

All values are constants at the top of `quiz_app/utils.py` and can be
changed there.

| Setting | Value | Reason |
|---|---|---|
| `MAX_VIDEO_SECONDS` | `15 * 60` (15 minutes) | The quiz is created inside the request, and transcribing with Whisper on the CPU takes several minutes for longer videos. Longer videos and livestreams would block the server for a long time, so they are rejected with 400 before anything is downloaded. |
| `GEMINI_MODEL` | `gemini-3.5-flash` | `gemini-2.5-flash` is not available for new API keys (404). |
| `GEMINI_RETRY_ATTEMPTS`, `GEMINI_RETRY_CODES` | 3 attempts on 429 / 503 | Gemini often answers with 503 ("high demand"). The request is retried automatically before it fails with 500. |
| `GEMINI_TIMEOUT_MS` | `60_000` (60 seconds per attempt) | A hanging Gemini request must not block the server forever. |
| `WHISPER_MODEL` | `base` | A compromise between speed and transcript quality. The model is loaded once and then reused. |
