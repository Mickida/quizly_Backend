import functools
import json
import os
import re
import tempfile
from urllib.parse import parse_qs, urlparse

import httpx
import whisper
import yt_dlp
from django.conf import settings
from django.db import transaction
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
from yt_dlp.utils import DownloadError

from quiz_app.models import Question, Quiz

YOUTUBE_HOSTS = {'youtube.com', 'www.youtube.com', 'm.youtube.com'}
SHORT_LINK_HOST = 'youtu.be'
VIDEO_ID_LENGTH = 11
VIDEO_ID_EXTRA_CHARS = '-_'  # allowed besides letters and digits
WHISPER_MODEL = 'base'
GEMINI_MODEL = 'gemini-3.5-flash'
GEMINI_TIMEOUT_MS = 60_000
GEMINI_RETRY_ATTEMPTS = 3
GEMINI_RETRY_CODES = [429, 503]  # rate limit, overloaded
MAX_VIDEO_SECONDS = 15 * 60  # longer videos block the request too long
QUESTION_COUNT = 10
OPTION_COUNT = 4
MAX_TEXT_LENGTH = 255  # max_length of Quiz.title / Question.answer

QUIZ_PROMPT = (
    'Based on the following transcript, generate a quiz in valid JSON '
    'format.\n\n'
    'The quiz must follow this exact structure:\n\n'
    '{{\n'
    '  "title": "Create a concise quiz title based on the topic of the '
    'transcript.",\n'
    '  "description": "Summarize the transcript in no more than 150 '
    'characters. Do not include any quiz questions or answers.",\n'
    '  "questions": [\n'
    '    {{\n'
    '      "question_title": "The question goes here.",\n'
    '      "question_options": ["Option A", "Option B", "Option C", '
    '"Option D"],\n'
    '      "answer": "The correct answer from the above options"\n'
    '    }},\n'
    '    ...\n'
    '    (exactly 10 questions)\n'
    '  ]\n'
    '}}\n\n'
    'Requirements:\n'
    '- Each question must have exactly 4 distinct answer options.\n'
    '- Only one correct answer is allowed per question, and it must be '
    "present in 'question_options'.\n"
    '- The output must be valid JSON and parsable as-is (e.g., using '
    "Python's json.loads).\n"
    '- Do not include explanations, comments, or any text outside the '
    'JSON.\n\n'
    'Transcript:\n{transcript}\n'
)


class QuizGenerationError(Exception):
    """Raised when no valid quiz can be generated from a transcript."""


def extract_video_id(url):
    """Return the video ID of a YouTube URL, or None if there is none.

    Supported: youtube.com/watch?v=<id> and youtu.be/<id>.
    """
    parsed = urlparse(url.strip())
    host = (parsed.hostname or '').lower()
    video_id = None
    if host in YOUTUBE_HOSTS and parsed.path == '/watch':
        video_id = parse_qs(parsed.query).get('v', [''])[0]
    elif host == SHORT_LINK_HOST:
        video_id = parsed.path.strip('/')
    if parsed.scheme in ('http', 'https') and is_video_id(video_id):
        return video_id
    return None


def is_video_id(value):
    """Return True if value looks like an 11 character YouTube ID."""
    if not value or len(value) != VIDEO_ID_LENGTH:
        return False
    return all(c.isalnum() or c in VIDEO_ID_EXTRA_CHARS for c in value)


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
        info = ydl.extract_info(video_url, download=False)
        check_video_info(info)
        ydl.download([video_url])
        return ydl.prepare_filename(info)


def check_video_info(info):
    """Reject livestreams and videos without or above the length limit."""
    duration = info.get('duration')
    if info.get('is_live') or duration is None:
        raise DownloadError('Livestreams are not supported.')
    if duration > MAX_VIDEO_SECONDS:
        raise DownloadError('Video is too long.')


@functools.lru_cache(maxsize=1)
def load_whisper_model():
    """Load the Whisper model once and reuse it for later requests."""
    return whisper.load_model(WHISPER_MODEL)


def transcribe_audio(audio_path):
    """Transcribe an audio file to text with Whisper."""
    model = load_whisper_model()
    result = model.transcribe(audio_path, fp16=False)
    return result['text'].strip()


def get_transcript(video_url):
    """Download a video's audio temporarily and return its transcript."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        audio_path = download_audio(video_url, tmp)
        return transcribe_audio(audio_path)


def build_prompt(transcript):
    """Insert the transcript into the quiz prompt template."""
    return QUIZ_PROMPT.format(transcript=transcript)


def build_gemini_client():
    """Return a Gemini client with a timeout and retries on overload."""
    # Repeat the request up to 3 times if Gemini answers 429 or 503.
    retry = genai_types.HttpRetryOptions(
        attempts=GEMINI_RETRY_ATTEMPTS, http_status_codes=GEMINI_RETRY_CODES
    )
    # Give up a single attempt after 60 seconds (value in milliseconds).
    options = genai_types.HttpOptions(
        timeout=GEMINI_TIMEOUT_MS, retry_options=retry
    )
    return genai.Client(api_key=settings.GEMINI_API_KEY, http_options=options)


def request_quiz_text(prompt):
    """Send the prompt to Gemini and return the raw response text."""
    client = build_gemini_client()
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL, contents=prompt
        )
    # APIError: Gemini answered with an error, HTTPError: network/timeout.
    except (genai_errors.APIError, httpx.HTTPError) as error:
        raise QuizGenerationError('Gemini request failed.') from error
    if not response.text:
        raise QuizGenerationError('Gemini returned an empty response.')
    return response.text


def strip_markdown_fences(text):
    """Remove leading and trailing Markdown code fences from text."""
    cleaned = re.sub(r'^\s*```[a-zA-Z]*\s*', '', text)
    return re.sub(r'\s*```\s*$', '', cleaned)


def parse_quiz_data(raw_text):
    """Turn the raw Gemini text into validated quiz data."""
    try:
        data = json.loads(strip_markdown_fences(raw_text))
    except json.JSONDecodeError as error:
        raise QuizGenerationError('Response is not valid JSON.') from error
    validate_quiz(data)
    data.setdefault('description', '')
    return data


def validate_quiz(data):
    """Check the quiz has a title and exactly ten valid questions."""
    if not isinstance(data, dict) or not is_text(data.get('title'),
                                                 MAX_TEXT_LENGTH):
        raise QuizGenerationError('Quiz title is missing or too long.')
    if not isinstance(data.get('description', ''), str):
        raise QuizGenerationError('Quiz description must be text.')
    questions = data.get('questions')
    if not isinstance(questions, list) or len(questions) != QUESTION_COUNT:
        raise QuizGenerationError('Quiz must have exactly 10 questions.')
    for question in questions:
        validate_question(question)


def validate_question(question):
    """Check a question has a title, four distinct options and an answer."""
    if not isinstance(question, dict):
        raise QuizGenerationError('Question must be an object.')
    if not is_text(question.get('question_title')):
        raise QuizGenerationError('Question title is missing.')
    options = question.get('question_options')
    if not has_distinct_options(options):
        raise QuizGenerationError('Question needs 4 distinct options.')
    answer = question.get('answer')
    if not is_text(answer, MAX_TEXT_LENGTH) or answer not in options:
        raise QuizGenerationError('Answer is not a valid option.')


def is_text(value, max_length=None):
    """Return True for a non-blank string within an optional length."""
    if not isinstance(value, str) or not value.strip():
        return False
    return max_length is None or len(value) <= max_length


def has_distinct_options(options):
    """Return True for a list of exactly four distinct strings."""
    return (
        isinstance(options, list)
        and len(options) == OPTION_COUNT
        and all(isinstance(option, str) for option in options)
        and len(set(options)) == OPTION_COUNT
    )


def generate_quiz_data(transcript):
    """Generate validated quiz data for a transcript with Gemini."""
    if not transcript.strip():
        raise QuizGenerationError('Transcript is empty.')
    return parse_quiz_data(request_quiz_text(build_prompt(transcript)))


def generate_quiz_from_video(video_url):
    """Run the full pipeline from a video URL to validated quiz data."""
    return generate_quiz_data(get_transcript(video_url))


@transaction.atomic
def create_quiz(user, video_url, quiz_data):
    """Save a generated quiz and its questions in one transaction."""
    quiz = Quiz.objects.create(
        user=user,
        video_url=video_url,
        title=quiz_data['title'],
        description=quiz_data['description'],
    )
    Question.objects.bulk_create(
        build_question(quiz, item) for item in quiz_data['questions']
    )
    return quiz


def build_question(quiz, item):
    """Build an unsaved Question from one generated question item."""
    return Question(
        quiz=quiz,
        question_title=item['question_title'],
        question_options=item['question_options'],
        answer=item['answer'],
    )
