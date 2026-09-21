"""Admin panel -- this is where the club sets up the questions."""

from django import forms
from django.contrib import admin
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html

from .models import Answer, Attempt, Choice, Question, Quiz

admin.site.site_header = "Daffodil AI Club — Quiz Admin"
admin.site.site_title = "AI Club Quiz Admin"
admin.site.index_title = "Manage the newcomer quiz"


class ChoiceInlineFormSet(forms.BaseInlineFormSet):
    """Every question needs exactly one correct option."""

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        correct = 0
        live = 0
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue
            live += 1
            if form.cleaned_data.get("is_correct"):
                correct += 1
        if live and live < 2:
            raise forms.ValidationError("Give the question at least two options.")
        if live and correct != 1:
            raise forms.ValidationError(
                f"Tick exactly one option as correct — you ticked {correct}."
            )


class ChoiceInline(admin.TabularInline):
    model = Choice
    formset = ChoiceInlineFormSet
    extra = 4
    fields = ("order", "text", "is_correct")
    ordering = ("order", "id")


class QuestionInline(admin.TabularInline):
    """Read-only overview on the quiz page, with a link into each question."""

    model = Question
    extra = 0
    fields = ("order", "text", "points", "options_summary", "edit_link")
    readonly_fields = ("options_summary", "edit_link")
    ordering = ("order", "id")
    show_change_link = False

    @admin.display(description="Options")
    def options_summary(self, obj):
        if not obj.pk:
            return "—"
        total = obj.choices.count()
        correct = obj.choices.filter(is_correct=True).count()
        if total == 0:
            return format_html('<span style="color:#b91c1c">no options yet</span>')
        if correct != 1:
            return format_html(
                '<span style="color:#b91c1c">{} options, {} marked correct</span>', total, correct
            )
        return format_html('<span style="color:#15803d">{} options ✓</span>', total)

    @admin.display(description="")
    def edit_link(self, obj):
        if not obj.pk:
            return "—"
        url = reverse("admin:quiz_question_change", args=[obj.pk])
        return format_html('<a class="button" href="{}">Edit options</a>', url)


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "question_count", "seconds_per_question", "attempts_count")
    list_filter = ("is_active",)
    inlines = [QuestionInline]
    fieldsets = (
        (None, {"fields": ("title", "intro", "is_active")}),
        (
            "Rules",
            {
                "fields": ("seconds_per_question", "pass_percentage", "show_answer_review"),
                "description": "Timer is per question. Set seconds to 0 to remove the timer entirely.",
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_attempts=Count("attempts", distinct=True))

    @admin.display(description="Questions")
    def question_count(self, obj):
        return obj.questions.count()

    @admin.display(description="Attempts", ordering="_attempts")
    def attempts_count(self, obj):
        return obj._attempts


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("order", "short_text", "quiz", "points", "correct_answer")
    list_display_links = ("short_text",)
    list_filter = ("quiz",)
    list_editable = ("order",)
    search_fields = ("text", "explanation")
    inlines = [ChoiceInline]
    fields = ("quiz", "order", "text", "points", "explanation")

    @admin.display(description="Question")
    def short_text(self, obj):
        return obj.text[:80] + ("…" if len(obj.text) > 80 else "")

    @admin.display(description="Correct answer")
    def correct_answer(self, obj):
        choice = obj.correct_choice
        if not choice:
            return format_html('<span style="color:#b91c1c">not set</span>')
        return choice.text[:50]


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    can_delete = False
    fields = ("question", "choice", "is_correct")
    readonly_fields = ("question", "choice", "is_correct")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    """Results are read-only — a record of what actually happened."""

    list_display = ("name", "quiz", "score_display", "percentage_display", "duration_display", "completed_at")
    list_filter = ("quiz", "completed_at")
    search_fields = ("name",)
    date_hierarchy = "started_at"
    inlines = [AnswerInline]
    readonly_fields = (
        "token", "quiz", "name", "score", "total", "correct_count",
        "started_at", "completed_at", "duration_display",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="Score", ordering="score")
    def score_display(self, obj):
        return f"{obj.score} / {obj.total}"

    @admin.display(description="%")
    def percentage_display(self, obj):
        return f"{obj.percentage}%"
