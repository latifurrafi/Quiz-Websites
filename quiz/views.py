"""Views for the newcomer quiz.

Flow: home -> start (name) -> play -> submit -> result.

Correct answers are never sent to the browser while the quiz is running. The
page receives questions and options only; scoring happens here, on submit.
"""

import json

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import StartForm
from .models import Answer, Attempt, Choice, Quiz

SESSION_KEY = "attempt_tokens"


def _remember(request, token):
    """Track which attempts belong to this browser, so results stay private."""
    tokens = request.session.get(SESSION_KEY, [])
    token = str(token)
    if token not in tokens:
        tokens.append(token)
        request.session[SESSION_KEY] = tokens[-20:]


def _owns(request, attempt):
    return str(attempt.token) in request.session.get(SESSION_KEY, [])


def _base_context():
    return {
        "site_name": settings.SITE_NAME,
        "site_tagline": settings.SITE_TAGLINE,
    }


def home(request):
    """Landing page: the club, the quiz, and the name form."""
    quiz = Quiz.get_active()
    context = _base_context()
    context.update(
        {
            "quiz": quiz,
            "form": StartForm(),
            "question_count": quiz.question_count if quiz else 0,
            "estimated_minutes": (
                max(1, round(quiz.estimated_seconds / 60)) if quiz and quiz.estimated_seconds else None
            ),
        }
    )
    return render(request, "quiz/home.html", context)


@require_POST
def start(request):
    """Create an attempt from the submitted name and send them into the quiz."""
    quiz = Quiz.get_active()
    if not quiz or quiz.question_count == 0:
        return redirect("quiz:home")

    form = StartForm(request.POST)
    if not form.is_valid():
        context = _base_context()
        context.update(
            {
                "quiz": quiz,
                "form": form,
                "question_count": quiz.question_count,
                "estimated_minutes": (
                    max(1, round(quiz.estimated_seconds / 60)) if quiz.estimated_seconds else None
                ),
            }
        )
        return render(request, "quiz/home.html", context, status=400)

    attempt = Attempt.objects.create(
        quiz=quiz,
        name=form.cleaned_data["name"],
        total=quiz.total_points,
    )
    _remember(request, attempt.token)
    return redirect("quiz:play", token=attempt.token)


def play(request, token):
    """The quiz itself. Ships questions and options — never the answer key."""
    attempt = get_object_or_404(Attempt.objects.select_related("quiz"), token=token)
    if not _owns(request, attempt):
        return redirect("quiz:home")
    if attempt.is_complete:
        return redirect("quiz:result", token=attempt.token)

    quiz = attempt.quiz
    payload = [
        {
            "id": q.id,
            "text": q.text,
            "points": q.points,
            "choices": [{"id": c.id, "text": c.text} for c in q.choices.all()],
        }
        for q in quiz.questions.prefetch_related("choices")
    ]

    context = _base_context()
    context.update(
        {
            "attempt": attempt,
            "quiz": quiz,
            "questions": payload,
            "seconds_per_question": quiz.seconds_per_question,
            "submit_url": reverse("quiz:submit", args=[attempt.token]),
            "result_url": reverse("quiz:result", args=[attempt.token]),
        }
    )
    return render(request, "quiz/play.html", context)


@require_POST
def submit(request, token):
    """Score the attempt. Expects {"answers": {question_id: choice_id|null}}."""
    attempt = get_object_or_404(Attempt.objects.select_related("quiz"), token=token)
    if not _owns(request, attempt):
        return JsonResponse({"error": "not_yours"}, status=403)

    result_url = reverse("quiz:result", args=[attempt.token])
    if attempt.is_complete:
        return JsonResponse({"ok": True, "redirect": result_url})

    try:
        submitted = json.loads(request.body or "{}").get("answers", {})
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"error": "bad_payload"}, status=400)
    if not isinstance(submitted, dict):
        return JsonResponse({"error": "bad_payload"}, status=400)

    questions = list(attempt.quiz.questions.prefetch_related("choices"))
    valid_choices = {
        c.id: c for c in Choice.objects.filter(question__in=questions).select_related("question")
    }

    score = 0
    correct_count = 0
    rows = []
    for question in questions:
        raw = submitted.get(str(question.id))
        choice = valid_choices.get(raw) if isinstance(raw, int) else None
        # Ignore a choice that belongs to a different question.
        if choice and choice.question_id != question.id:
            choice = None
        is_correct = bool(choice and choice.is_correct)
        if is_correct:
            score += question.points
            correct_count += 1
        rows.append(Answer(attempt=attempt, question=question, choice=choice, is_correct=is_correct))

    Answer.objects.bulk_create(rows, ignore_conflicts=True)

    attempt.score = score
    attempt.correct_count = correct_count
    attempt.total = sum(q.points for q in questions)
    attempt.completed_at = timezone.now()
    attempt.save(update_fields=["score", "correct_count", "total", "completed_at"])

    return JsonResponse({"ok": True, "redirect": result_url})


def result(request, token):
    """Congratulations screen, plus the answer review."""
    attempt = get_object_or_404(Attempt.objects.select_related("quiz"), token=token)
    if not _owns(request, attempt):
        return redirect("quiz:home")
    if not attempt.is_complete:
        return redirect("quiz:play", token=attempt.token)

    review = []
    if attempt.quiz.show_answer_review:
        answers = attempt.answers.select_related("question", "choice").prefetch_related(
            "question__choices"
        )
        for answer in answers:
            review.append(
                {
                    "question": answer.question,
                    "given": answer.choice,
                    "correct": answer.question.correct_choice,
                    "is_correct": answer.is_correct,
                    "skipped": answer.choice is None,
                }
            )

    context = _base_context()
    context.update({"attempt": attempt, "quiz": attempt.quiz, "review": review})
    return render(request, "quiz/result.html", context)
