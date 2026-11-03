from django.contrib.auth.models import User
from django.db import models


class Quiz(models.Model):
    """A quiz generated from a YouTube video for one user."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='quizzes'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    video_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'quizzes'

    def __str__(self):
        """Return the quiz title for the admin."""
        return self.title


class Question(models.Model):
    """A multiple-choice question with four options and one answer."""

    quiz = models.ForeignKey(
        Quiz, on_delete=models.CASCADE, related_name='questions'
    )
    question_title = models.TextField()
    question_options = models.JSONField()
    answer = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        """Return the question text for the admin."""
        return self.question_title
