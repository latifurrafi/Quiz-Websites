"""Data model for the AI Club newcomer quiz.

The site presents a single active quiz. `Quiz` still exists as a real model so
the club can prepare a new question set in the admin and switch to it without
touching code -- activating a quiz simply deactivates the others.
"""

import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Quiz(models.Model):
    """One set of questions. Exactly one quiz is live at a time."""

    title = models.CharField(max_length=160, default="AI Club Newcomer Quiz")
    intro = models.TextField(
        blank=True,
        help_text="Short line shown on the start screen, under the title.",
    )
    seconds_per_question = models.PositiveIntegerField(
        default=30,
        validators=[MaxValueValidator(600)],
        help_text="Countdown for each question. Set to 0 for no timer.",
    )
    pass_percentage = models.PositiveIntegerField(
        default=50,
        validators=[MaxValueValidator(100)],
        help_text="Score at or above this percentage counts as a pass.",
    )
    show_answer_review = models.BooleanField(
        default=True,
        help_text="Show participants the correct answers after they finish.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="The one quiz newcomers see. Turning this on turns the others off.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "quizzes"
        ordering = ["-is_active", "-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_active:
            Quiz.objects.exclude(pk=self.pk).filter(is_active=True).update(is_active=False)

    @classmethod
    def get_active(cls):
        return cls.objects.filter(is_active=True).prefetch_related("questions__choices").first()

    @property
    def question_count(self):
        return self.questions.count()

    @property
    def total_points(self):
        return sum(q.points for q in self.questions.all()) or 0

    @property
    def estimated_seconds(self):
        if not self.seconds_per_question:
            return 0
        return self.seconds_per_question * self.question_count


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField(help_text="The question itself.")
    explanation = models.TextField(
        blank=True,
        help_text="Optional. Shown in the answer review after the quiz ends.",
    )
    points = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    order = models.PositiveIntegerField(default=0, help_text="Lower numbers come first.")

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.order}. {self.text[:70]}"

    @property
    def correct_choice(self):
        return self.choices.filter(is_correct=True).first()


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=300)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{'OK  ' if self.is_correct else '--  '}{self.text[:60]}"


class Attempt(models.Model):
    """One newcomer's run through the quiz. Identified by an unguessable token."""

    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    name = models.CharField(max_length=80)

    score = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)
    correct_count = models.PositiveIntegerField(default=0)

    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-completed_at", "-started_at"]

    def __str__(self):
        state = "finished" if self.is_complete else "in progress"
        return f"{self.name} - {self.score}/{self.total} ({state})"

    @property
    def is_complete(self):
        return self.completed_at is not None

    @property
    def percentage(self):
        if not self.total:
            return 0
        return round(self.score / self.total * 100)

    @property
    def passed(self):
        return self.percentage >= self.quiz.pass_percentage

    @property
    def answered_count(self):
        """How many questions this attempt actually covered."""
        return self.answers.count()

    @property
    def missed_count(self):
        return max(0, self.answered_count - self.correct_count)

    @property
    def duration_seconds(self):
        if not self.completed_at:
            return 0
        return max(0, int((self.completed_at - self.started_at).total_seconds()))

    @property
    def duration_display(self):
        seconds = self.duration_seconds
        minutes, seconds = divmod(seconds, 60)
        return f"{minutes}m {seconds:02d}s" if minutes else f"{seconds}s"

    @property
    def headline(self):
        """The congratulation line, tuned to how well they did."""
        pct = self.percentage
        if pct == 100:
            return "Flawless."
        if pct >= 80:
            return "Outstanding."
        if pct >= self.quiz.pass_percentage:
            return "Well played."
        return "Good effort."


class Answer(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice = models.ForeignKey(
        Choice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Empty means the question was skipped or the timer ran out.",
    )
    is_correct = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["question__order", "question_id"]
        unique_together = [("attempt", "question")]

    def __str__(self):
        return f"{self.attempt.name} - Q{self.question.order}"
