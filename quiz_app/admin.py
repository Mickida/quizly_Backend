from django.contrib import admin

from quiz_app.models import Question, Quiz


class QuestionInline(admin.StackedInline):
    """Edit the questions of a quiz directly on the quiz page."""

    model = Question
    extra = 0


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    """Admin view for quizzes including their questions."""

    list_display = ['title', 'user', 'created_at']
    list_filter = ['created_at']
    search_fields = ['title', 'description', 'user__username']
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Admin view for editing single questions."""

    list_display = ['question_title', 'quiz', 'answer']
    search_fields = ['question_title']
