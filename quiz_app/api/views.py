from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from quiz_app.api.permissions import IsQuizOwner
from quiz_app.api.serializers import QuizSerializer
from quiz_app.models import Quiz


class QuizListView(generics.ListAPIView):
    """List all quizzes of the authenticated user."""

    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return only the requesting user's quizzes."""
        return Quiz.objects.filter(
            user=self.request.user
        ).prefetch_related('questions')


class QuizDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, partially update or delete one quiz of its owner."""

    queryset = Quiz.objects.prefetch_related('questions')
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated, IsQuizOwner]
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']
