import os
import re
import tempfile
from urllib.parse import parse_qs, urlparse

import whisper
import yt_dlp

VIDEO_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{11}$')
YOUTUBE_HOSTS = {'youtube.com', 'www.youtube.com', 'm.youtube.com'}
SHORT_LINK_HOSTS = {'youtu.be', 'www.youtu.be'}
PATH_PREFIXES = ('/shorts/', '/embed/', '/live/')
WHISPER_MODEL = 'base'


def extract_video_id(url):
    """Return the video ID of a YouTube URL, or None if there is none."""
    parsed = urlparse(url.strip())
    if parsed.scheme not in ('http', 'https'):
        return None
    candidate = find_id_candidate(parsed)
    if candidate and VIDEO_ID_PATTERN.match(candidate):
        return candidate
    return None


def find_id_candidate(parsed):
    """Return the part of a parsed YouTube URL that holds the ID."""
    host = (parsed.hostname or '').lower()
    if host in SHORT_LINK_HOSTS:
        return parsed.path.strip('/').split('/')[0]
    if host not in YOUTUBE_HOSTS:
        return None
    if parsed.path == '/watch':
        return parse_qs(parsed.query).get('v', [None])[0]
    for prefix in PATH_PREFIXES:
        if parsed.path.startswith(prefix):
            return parsed.path[len(prefix):].split('/')[0]
    return None


def build_watch_url(video_id):
    """Return the canonical watch URL that the frontend can embed."""
    return f'https://www.youtube.com/watch?v={video_id}'


def download_audio(video_url, target_dir):
    """Download the audio track of a video and return the file path."""
    options = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(target_dir, 'audio.%(ext)s'),
        'quiet': True,
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(video_url, download=True)
        return ydl.prepare_filename(info)


def transcribe_audio(audio_path):
    """Transcribe an audio file to text with Whisper."""
    model = whisper.load_model(WHISPER_MODEL)
    result = model.transcribe(audio_path, fp16=False)
    return result['text'].strip()


def get_transcript(video_url):
    """Download a video's audio temporarily and return its transcript."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        audio_path = download_audio(video_url, tmp)
        return transcribe_audio(audio_path)
