import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Question


def create_question(question_text, days):
    time = timezone.now() + datetime.timedelta(days=days)
    return Question.objects.create(question_text=question_text, pub_date=time)


class QuestionModelTests(TestCase):
    def test_future_question_is_not_recent(self):
        question = create_question("Future question.", days=30)
        self.assertIs(question.was_published_recently(), False)
        response = self.client.get(reverse("polls:index"))
        self.assertNotContains(response, "Future question.")
        self.assertQuerySetEqual(response.context["latest_question_list"], [])

    def test_was_published_recently_with_old_question(self):
        time = timezone.now() - datetime.timedelta(days=1, seconds=1)
        old_question = Question(pub_date=time)
        self.assertIs(old_question.was_published_recently(), False)

    def test_was_published_recently_with_recent_question(self):
        time = timezone.now() - datetime.timedelta(hours=23, minutes=59, seconds=59)
        recent_question = Question(pub_date=time)
        self.assertIs(recent_question.was_published_recently(), True)


class QuestionIndexViewTests(TestCase):
    def test_empty_index(self):
        response = self.client.get(reverse("polls:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No polls are available.")
        self.assertQuerySetEqual(response.context["latest_question_list"], [])

    def test_past_question(self):
        question = create_question("Past question.", days=-30)
        response = self.client.get(reverse("polls:index"))
        self.assertQuerySetEqual(response.context["latest_question_list"], [question])


class QuestionDetailViewTests(TestCase):
    def test_future_question(self):
        question = create_question("Future question.", days=5)
        response = self.client.get(reverse("polls:detail", args=(question.id,)))
        self.assertEqual(response.status_code, 404)

    def test_past_question(self):
        question = create_question("Past Question.", days=-5)
        response = self.client.get(reverse("polls:detail", args=(question.id,)))
        self.assertContains(response, question.question_text)


class VoteViewTests(TestCase):
    def test_vote_increments_selected_choice(self):
        question = create_question("Vote question.", days=-1)
        choice1 = question.choice_set.create(choice_text="A")
        choice2 = question.choice_set.create(choice_text="B")
        response = self.client.post(
            reverse("polls:vote", args=(question.id,)), {"choice": choice1.id}
        )
        self.assertRedirects(response, reverse("polls:results", args=(question.id,)))
        choice1.refresh_from_db()
        choice2.refresh_from_db()
        self.assertEqual(choice1.votes, 1)
        self.assertEqual(choice2.votes, 0)

    def test_vote_with_missing_choice_does_not_increment(self):
        question = create_question("Vote question.", days=-1)
        choice = question.choice_set.create(choice_text="A")
        response = self.client.post(reverse("polls:vote", args=(question.id,)), {})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You didn&#x27;t select a choice.")
        choice.refresh_from_db()
        self.assertEqual(choice.votes, 0)

    def test_vote_with_nonexistent_choice_does_not_increment(self):
        question = create_question("Vote question.", days=-1)
        choice = question.choice_set.create(choice_text="A")
        response = self.client.post(
            reverse("polls:vote", args=(question.id,)), {"choice": 99999}
        )
        self.assertEqual(response.status_code, 200)
        choice.refresh_from_db()
        self.assertEqual(choice.votes, 0)

    def test_vote_with_choice_of_other_question_does_not_increment(self):
        question = create_question("Vote question.", days=-1)
        other_question = create_question("Other question.", days=-1)
        own_choice = question.choice_set.create(choice_text="A")
        other_choice = other_question.choice_set.create(choice_text="B")
        response = self.client.post(
            reverse("polls:vote", args=(question.id,)), {"choice": other_choice.id}
        )
        self.assertEqual(response.status_code, 200)
        own_choice.refresh_from_db()
        other_choice.refresh_from_db()
        self.assertEqual(own_choice.votes, 0)
        self.assertEqual(other_choice.votes, 0)