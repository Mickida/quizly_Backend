import logging

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from yt_dlp.utils import DownloadError

from quiz_app.api.permissions import IsQuizOwner
from quiz_app.api.serializers import (
    QuizCreateResponseSerializer,
    QuizCreateSerializer,
    QuizSerializer,
)
from quiz_app.models import Quiz
from quiz_app.utils import (
    QuizGenerationError,
    create_quiz,
    generate_quiz_from_video,
)

logger = logging.getLogger(__name__)


class QuizListView(generics.ListCreateAPIView):
    """List the user's quizzes or create a new one from a YouTube URL."""

    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return only the requesting user's quizzes."""
        return Quiz.objects.filter(
            user=self.request.user
        ).prefetch_related('questions')

    def create(self, request, *args, **kwargs):
        """Generate a quiz from the submitted URL and save it."""
        serializer = QuizCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        video_url = serializer.validated_data['url']
        quiz_data, error_response = self.run_pipeline(video_url)
        if error_response is not None:
            return error_response
        quiz = create_quiz(request.user, video_url, quiz_data)
        data = QuizCreateResponseSerializer(quiz).data
        return Response(data, status=status.HTTP_201_CREATED)

    def run_pipeline(self, video_url):
        """Return (quiz_data, None) or (None, error_response)."""
        try:
            return generate_quiz_from_video(video_url), None
        except DownloadError:
            return None, Response(
                {'detail': 'Video could not be downloaded.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except QuizGenerationError as error:
            logger.warning('Quiz generation failed: %s', error)
            return None, Response(
                {'detail': 'Quiz generation failed.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class QuizDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, partially update or delete one quiz of its owner."""

    queryset = Quiz.objects.prefetch_related('questions')
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated, IsQuizOwner]
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']
