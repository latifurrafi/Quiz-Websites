"""End-to-end coverage of the newcomer quiz flow."""

import json

from django.test import TestCase
from django.urls import reverse

from .models import Attempt, Choice, Question, Quiz


class QuizFlowTests(TestCase):
    def setUp(self):
        self.quiz = Quiz.objects.create(
            title="Test Quiz", seconds_per_question=30, pass_percentage=50, is_active=True
        )
        for i in range(1, 5):
            q = Question.objects.create(
                quiz=self.quiz, text=f"Question {i}?", order=i, explanation=f"Because {i}."
            )
            for j in range(4):
                Choice.objects.create(
                    question=q, text=f"Option {j}", order=j, is_correct=(j == 0)
                )

    # -- helpers ----------------------------------------------------------
    def _start(self, name="Ada Lovelace"):
        res = self.client.post(reverse("quiz:start"), {"name": name})
        self.assertEqual(res.status_code, 302)
        return Attempt.objects.latest("started_at")

    def _answers(self, attempt, correct_count):
        """Build a payload answering `correct_count` questions correctly."""
        payload = {}
        for i, q in enumerate(attempt.quiz.questions.all()):
            choices = list(q.choices.all())
            payload[str(q.id)] = (choices[0] if i < correct_count else choices[1]).id
        return payload

    # -- tests ------------------------------------------------------------
    def test_home_renders_active_quiz(self):
        res = self.client.get(reverse("quiz:home"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Test Quiz")

    def test_name_is_required(self):
        res = self.client.post(reverse("quiz:start"), {"name": ""})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Attempt.objects.count(), 0)

    def test_name_is_normalised(self):
        attempt = self._start("  ada   LOVELACE  ")
        self.assertEqual(attempt.name, "ada LOVELACE")

    def test_play_page_never_leaks_the_answer_key(self):
        attempt = self._start()
        res = self.client.get(reverse("quiz:play", args=[attempt.token]))
        self.assertEqual(res.status_code, 200)
        body = res.content.decode()
        self.assertIn("Question 1?", body)
        self.assertNotIn("is_correct", body)
        shipped = res.context["questions"]
        self.assertEqual(len(shipped), 4)
        self.assertEqual(set(shipped[0]), {"id", "text", "points", "choices"})
        self.assertEqual(set(shipped[0]["choices"][0]), {"id", "text"})

    def test_full_marks(self):
        attempt = self._start()
        res = self.client.post(
            reverse("quiz:submit", args=[attempt.token]),
            data=json.dumps({"answers": self._answers(attempt, 4)}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        attempt.refresh_from_db()
        self.assertEqual((attempt.score, attempt.correct_count, attempt.percentage), (4, 4, 100))
        self.assertTrue(attempt.passed)
        self.assertEqual(attempt.headline, "Flawless.")

    def test_partial_score_and_missed_count(self):
        attempt = self._start()
        self.client.post(
            reverse("quiz:submit", args=[attempt.token]),
            data=json.dumps({"answers": self._answers(attempt, 1)}),
            content_type="application/json",
        )
        attempt.refresh_from_db()
        self.assertEqual(attempt.score, 1)
        self.assertEqual(attempt.percentage, 25)
        self.assertEqual(attempt.missed_count, 3)
        self.assertFalse(attempt.passed)

    def test_skipped_questions_are_recorded(self):
        attempt = self._start()
        self.client.post(
            reverse("quiz:submit", args=[attempt.token]),
            data=json.dumps({"answers": {}}),
            content_type="application/json",
        )
        attempt.refresh_from_db()
        self.assertEqual(attempt.score, 0)
        self.assertEqual(attempt.answers.count(), 4)
        self.assertTrue(all(a.choice is None for a in attempt.answers.all()))

    def test_choice_from_another_question_is_rejected(self):
        """Pairing question 1 with question 2's correct option must not score."""
        attempt = self._start()
        questions = list(attempt.quiz.questions.all())
        foreign = questions[1].choices.filter(is_correct=True).first()
        self.client.post(
            reverse("quiz:submit", args=[attempt.token]),
            data=json.dumps({"answers": {str(questions[0].id): foreign.id}}),
            content_type="application/json",
        )
        attempt.refresh_from_db()
        self.assertEqual(attempt.score, 0)

    def test_resubmitting_does_not_change_the_score(self):
        attempt = self._start()
        url = reverse("quiz:submit", args=[attempt.token])
        self.client.post(url, data=json.dumps({"answers": self._answers(attempt, 4)}),
                         content_type="application/json")
        self.client.post(url, data=json.dumps({"answers": self._answers(attempt, 0)}),
                         content_type="application/json")
        attempt.refresh_from_db()
        self.assertEqual(attempt.score, 4)
        self.assertEqual(attempt.answers.count(), 4)

    def test_result_shows_name_score_and_review(self):
        attempt = self._start("Grace Hopper")
        self.client.post(
            reverse("quiz:submit", args=[attempt.token]),
            data=json.dumps({"answers": self._answers(attempt, 3)}),
            content_type="application/json",
        )
        res = self.client.get(reverse("quiz:result", args=[attempt.token]))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Grace Hopper")
        self.assertContains(res, "Congratulations")
        self.assertEqual(len(res.context["review"]), 4)
        self.assertContains(res, "Because 1.")

    def test_answer_review_can_be_switched_off(self):
        self.quiz.show_answer_review = False
        self.quiz.save()
        attempt = self._start()
        self.client.post(
            reverse("quiz:submit", args=[attempt.token]),
            data=json.dumps({"answers": self._answers(attempt, 2)}),
            content_type="application/json",
        )
        res = self.client.get(reverse("quiz:result", args=[attempt.token]))
        self.assertEqual(res.context["review"], [])

    def test_another_browser_cannot_read_your_result(self):
        attempt = self._start()
        self.client.post(
            reverse("quiz:submit", args=[attempt.token]),
            data=json.dumps({"answers": self._answers(attempt, 4)}),
            content_type="application/json",
        )
        stranger = self.client_class()
        self.assertEqual(
            stranger.get(reverse("quiz:result", args=[attempt.token])).status_code, 302
        )
        self.assertEqual(
            stranger.post(
                reverse("quiz:submit", args=[attempt.token]),
                data=json.dumps({"answers": {}}),
                content_type="application/json",
            ).status_code,
            403,
        )

    def test_finished_attempt_redirects_away_from_the_quiz(self):
        attempt = self._start()
        self.client.post(
            reverse("quiz:submit", args=[attempt.token]),
            data=json.dumps({"answers": self._answers(attempt, 4)}),
            content_type="application/json",
        )
        res = self.client.get(reverse("quiz:play", args=[attempt.token]))
        self.assertRedirects(res, reverse("quiz:result", args=[attempt.token]))

    def test_next_participant_hides_the_previous_result(self):
        """The whole point on a shared computer: no peeking at the last person."""
        attempt = self._start("Alice")
        self.client.post(
            reverse("quiz:submit", args=[attempt.token]),
            data=json.dumps({"answers": self._answers(attempt, 4)}),
            content_type="application/json",
        )
        # Alice can see her own result.
        self.assertEqual(
            self.client.get(reverse("quiz:result", args=[attempt.token])).status_code, 200
        )

        # She hands the machine over.
        res = self.client.post(reverse("quiz:reset"))
        self.assertRedirects(res, reverse("quiz:home"))

        # The next person, same browser, cannot reach her result or her quiz.
        self.assertRedirects(
            self.client.get(reverse("quiz:result", args=[attempt.token])),
            reverse("quiz:home"),
        )
        self.assertRedirects(
            self.client.get(reverse("quiz:play", args=[attempt.token])),
            reverse("quiz:home"),
        )

    def test_next_participant_keeps_the_stored_result(self):
        """Clearing the session must not delete anything the club needs."""
        attempt = self._start("Bob")
        self.client.post(
            reverse("quiz:submit", args=[attempt.token]),
            data=json.dumps({"answers": self._answers(attempt, 2)}),
            content_type="application/json",
        )
        self.client.post(reverse("quiz:reset"))

        attempt.refresh_from_db()
        self.assertEqual(attempt.score, 2)
        self.assertTrue(attempt.is_complete)
        self.assertEqual(Attempt.objects.count(), 1)

    def test_next_participant_can_take_it_again(self):
        """Back-to-back runs on the same browser produce separate attempts."""
        first = self._start("Carol")
        self.client.post(
            reverse("quiz:submit", args=[first.token]),
            data=json.dumps({"answers": self._answers(first, 4)}),
            content_type="application/json",
        )
        self.client.post(reverse("quiz:reset"))

        second = self._start("Dave")
        self.assertNotEqual(first.token, second.token)
        self.assertEqual(
            self.client.get(reverse("quiz:play", args=[second.token])).status_code, 200
        )
        self.assertEqual(Attempt.objects.count(), 2)
        self.assertEqual(
            sorted(Attempt.objects.values_list("name", flat=True)), ["Carol", "Dave"]
        )

    def test_reset_requires_post(self):
        """A GET must not clear the session -- link prefetching would wipe it."""
        self.assertEqual(self.client.get(reverse("quiz:reset")).status_code, 405)

    def test_malformed_payload_is_rejected(self):
        attempt = self._start()
        res = self.client.post(
            reverse("quiz:submit", args=[attempt.token]),
            data="not json",
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)


class QuizModelTests(TestCase):
    def test_activating_a_quiz_deactivates_the_others(self):
        first = Quiz.objects.create(title="First", is_active=True)
        second = Quiz.objects.create(title="Second", is_active=True)
        first.refresh_from_db()
        self.assertFalse(first.is_active)
        self.assertEqual(Quiz.get_active(), second)

    def test_home_copes_with_no_quiz(self):
        res = self.client.get(reverse("quiz:home"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "No quiz is live yet")

    def test_start_is_refused_when_no_quiz_is_live(self):
        res = self.client.post(reverse("quiz:start"), {"name": "Nobody"})
        self.assertRedirects(res, reverse("quiz:home"))
        self.assertEqual(Attempt.objects.count(), 0)


class AdminPanelTests(TestCase):
    """The admin is where the club actually builds the quiz, so it gets covered."""

    def setUp(self):
        from django.contrib.auth.models import User

        User.objects.create_superuser("organiser", "organiser@example.com", "test-pass-not-real")
        self.client.login(username="organiser", password="test-pass-not-real")
        self.quiz = Quiz.objects.create(title="Admin Quiz", is_active=True)
        self.question = Question.objects.create(quiz=self.quiz, text="Pick one", order=1)
        for j in range(4):
            Choice.objects.create(question=self.question, text=f"Opt {j}", order=j, is_correct=(j == 0))

    def test_admin_pages_load(self):
        from django.urls import reverse as r

        for name, args in [
            ("admin:index", []),
            ("admin:quiz_quiz_changelist", []),
            ("admin:quiz_quiz_change", [self.quiz.pk]),
            ("admin:quiz_question_changelist", []),
            ("admin:quiz_question_change", [self.question.pk]),
            ("admin:quiz_attempt_changelist", []),
        ]:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(r(name, args=args)).status_code, 200)

    def _choice_post(self, correct_flags, text_overrides=None):
        """Build a question change-form POST with the given correctness flags."""
        choices = list(self.question.choices.all())
        data = {
            "quiz": self.quiz.pk,
            "order": 1,
            "text": "Pick one",
            "points": 1,
            "explanation": "",
            "choices-TOTAL_FORMS": str(len(choices)),
            "choices-INITIAL_FORMS": str(len(choices)),
            "choices-MIN_NUM_FORMS": "0",
            "choices-MAX_NUM_FORMS": "1000",
        }
        for i, choice in enumerate(choices):
            data[f"choices-{i}-id"] = choice.pk
            data[f"choices-{i}-question"] = self.question.pk
            data[f"choices-{i}-order"] = choice.order
            data[f"choices-{i}-text"] = (text_overrides or {}).get(i, choice.text)
            if correct_flags[i]:
                data[f"choices-{i}-is_correct"] = "on"
        return data

    def test_admin_rejects_two_correct_answers(self):
        from django.urls import reverse as r

        res = self.client.post(
            r("admin:quiz_question_change", args=[self.question.pk]),
            self._choice_post([True, True, False, False]),
        )
        self.assertEqual(res.status_code, 200)  # redisplayed with an error
        self.assertContains(res, "you ticked 2")

    def test_admin_rejects_no_correct_answer(self):
        from django.urls import reverse as r

        res = self.client.post(
            r("admin:quiz_question_change", args=[self.question.pk]),
            self._choice_post([False, False, False, False]),
        )
        self.assertContains(res, "you ticked 0")

    def test_admin_accepts_exactly_one_correct_answer(self):
        from django.urls import reverse as r

        res = self.client.post(
            r("admin:quiz_question_change", args=[self.question.pk]),
            self._choice_post([False, False, True, False]),
        )
        self.assertEqual(res.status_code, 302)  # saved
        self.assertEqual(self.question.correct_choice.text, "Opt 2")

    def test_results_are_read_only(self):
        from django.urls import reverse as r

        attempt = Attempt.objects.create(quiz=self.quiz, name="Someone", total=1)
        res = self.client.get(r("admin:quiz_attempt_change", args=[attempt.pk]))
        self.assertEqual(res.status_code, 200)
        self.assertNotContains(res, 'name="_save"')
