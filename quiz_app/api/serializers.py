from rest_framework import serializers

from quiz_app.models import Question, Quiz


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
