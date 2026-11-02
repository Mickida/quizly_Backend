from rest_framework import serializers

from quiz_app.models import Question, Quiz
from quiz_app.utils import build_watch_url, extract_video_id


class QuestionSerializer(serializers.ModelSerializer):
    """Question as shown in quiz lists and details."""

    class Meta:
        model = Question
        fields = ['id', 'question_title', 'question_options', 'answer']


class QuizSerializer(serializers.ModelSerializer):
    """Quiz with its questions; only title and description are writable."""

    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = [
            'id', 'title', 'description', 'created_at', 'updated_at',
            'video_url', 'questions',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'video_url']


class QuizCreateSerializer(serializers.Serializer):
    """Validate the YouTube URL and return its canonical form."""

    url = serializers.CharField()

    def validate_url(self, value):
        """Accept only YouTube video URLs and normalize them."""
        video_id = extract_video_id(value)
        if video_id is None:
            raise serializers.ValidationError(
                'Please provide a valid YouTube video URL.'
            )
        return build_watch_url(video_id)


class QuestionDetailSerializer(QuestionSerializer):
    """Question including timestamps, used in the create response."""

    class Meta(QuestionSerializer.Meta):
        fields = QuestionSerializer.Meta.fields + ['created_at', 'updated_at']


class QuizCreateResponseSerializer(QuizSerializer):
    """Quiz returned after creation, with timestamped questions."""

    questions = QuestionDetailSerializer(many=True, read_only=True)
