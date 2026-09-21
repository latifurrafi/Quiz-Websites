"""Load a starter 10-question AI quiz so the site works out of the box.

    python manage.py seed_quiz             # create if missing
    python manage.py seed_quiz --reset     # wipe questions and reload
    python manage.py seed_quiz --if-empty  # only when there is no quiz at all
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from quiz.models import Choice, Question, Quiz

QUESTIONS = [
    (
        "What does the “AI” in AI Club actually stand for?",
        ["Automated Integration", "Artificial Intelligence", "Applied Informatics", "Adaptive Inference"],
        1,
        "Artificial Intelligence — the field of building systems that perform tasks normally requiring human intelligence.",
    ),
    (
        "Which of these is a supervised learning task?",
        [
            "Grouping customers into segments with no labels",
            "Predicting tomorrow's temperature from labelled historical data",
            "Reducing 100 features down to 2 for plotting",
            "An agent learning to walk by trial and error",
        ],
        1,
        "Supervised learning trains on labelled examples. The others describe clustering, dimensionality reduction and reinforcement learning.",
    ),
    (
        "In a neural network, what is an “epoch”?",
        [
            "One full pass over the entire training dataset",
            "A single neuron's activation value",
            "The gap between two layers",
            "The time taken to make one prediction",
        ],
        0,
        "One epoch means the model has seen every training example exactly once.",
    ),
    (
        "What does GPU stand for, and why does deep learning lean on it?",
        [
            "General Processing Unit — it has more memory",
            "Graphics Processing Unit — it runs many operations in parallel",
            "Global Prediction Unit — it is built for neural networks",
            "Grouped Pipeline Unit — it stores models efficiently",
        ],
        1,
        "Graphics Processing Unit. Training is mostly matrix maths, and a GPU runs thousands of those operations at once.",
    ),
    (
        "Which term describes a model that performs brilliantly on training data but poorly on new data?",
        ["Underfitting", "Regularisation", "Overfitting", "Normalisation"],
        2,
        "Overfitting — the model has memorised the training set instead of learning patterns that generalise.",
    ),
    (
        "What does the “T” in GPT stand for?",
        ["Trained", "Transformer", "Transfer", "Tokeniser"],
        1,
        "Generative Pre-trained Transformer. The transformer architecture was introduced in the 2017 paper “Attention Is All You Need”.",
    ),
    (
        "Which Python library is most associated with building deep learning models?",
        ["NumPy", "Matplotlib", "PyTorch", "Requests"],
        2,
        "PyTorch (alongside TensorFlow) is the standard for deep learning. NumPy handles arrays, Matplotlib plots, Requests does HTTP.",
    ),
    (
        "In machine learning, what is a “feature”?",
        [
            "A bug that turned out to be useful",
            "An individual measurable property used as model input",
            "The final output of the model",
            "A layer inside a neural network",
        ],
        1,
        "A feature is one input variable — for example a house's size, age or location when predicting its price.",
    ),
    (
        "What is the main purpose of splitting data into training and test sets?",
        [
            "To make training run faster",
            "To measure how the model performs on data it has never seen",
            "To reduce the file size of the dataset",
            "To balance the number of classes",
        ],
        1,
        "The test set is held back so your accuracy figure reflects real generalisation, not memorisation.",
    ),
    (
        "What does it mean when a language model “hallucinates”?",
        [
            "It runs out of memory mid-response",
            "It refuses to answer the question",
            "It produces confident, fluent output that is factually wrong",
            "It repeats the same sentence over and over",
        ],
        2,
        "Hallucination is fluent, confident output that is simply not true — which is why you verify anything important a model tells you.",
    ),
]


class Command(BaseCommand):
    help = "Create the starter 10-question AI Club quiz."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing questions on the active quiz and reload them.",
        )
        parser.add_argument(
            "--if-empty",
            action="store_true",
            help="Do nothing if any quiz already exists. Used on container start "
                 "so a restart never touches questions the club has written.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["if_empty"] and Quiz.objects.exists():
            self.stdout.write("A quiz already exists — leaving it alone.")
            return

        quiz, created = Quiz.objects.get_or_create(
            title="AI Club Newcomer Quiz",
            defaults={
                "intro": "Ten questions on the fundamentals. No preparation needed — "
                         "we just want to see how you think.",
                "seconds_per_question": 30,
                "pass_percentage": 50,
                "is_active": True,
            },
        )

        if quiz.questions.exists():
            if not options["reset"]:
                self.stdout.write(
                    self.style.WARNING(
                        f'"{quiz.title}" already has {quiz.questions.count()} questions. '
                        "Run with --reset to replace them."
                    )
                )
                return
            quiz.questions.all().delete()
            self.stdout.write("Cleared existing questions.")

        for index, (text, options_list, correct_index, explanation) in enumerate(QUESTIONS, start=1):
            question = Question.objects.create(
                quiz=quiz, text=text, order=index, points=1, explanation=explanation
            )
            Choice.objects.bulk_create(
                [
                    Choice(question=question, text=choice_text, order=i, is_correct=(i == correct_index))
                    for i, choice_text in enumerate(options_list)
                ]
            )

        quiz.is_active = True
        quiz.save()

        verb = "Created" if created else "Reloaded"
        self.stdout.write(
            self.style.SUCCESS(
                f'{verb} "{quiz.title}" with {len(QUESTIONS)} questions '
                f"({quiz.seconds_per_question}s per question)."
            )
        )
