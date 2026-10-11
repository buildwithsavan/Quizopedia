from django.core.management.base import BaseCommand
from reports.models import Subject, Question, Option

class Command(BaseCommand):
    help = 'Seeds 3 subjects, 6 questions (2 per subject), and 24 options (4 per question with 1 correct answer).'

    def handle(self, *args, **kwargs):
        self.stdout.write("Inspecting and preparing Subject, Question, and Option records...")

        Option.objects.all().delete()
        Question.objects.all().delete()
        Subject.objects.all().delete()

        quiz_data = [
            {
                "subject": "Mathematics",
                "questions": [
                    {
                        "text": "What is the square root of 144?",
                        "options": [
                            ("12", True),
                            ("14", False),
                            ("16", False),
                            ("10", False),
                        ]
                    },
                    {
                        "text": "What is 15 * 8?",
                        "options": [
                            ("110", False),
                            ("120", True),
                            ("125", False),
                            ("140", False),
                        ]
                    }
                ]
            },
            {
                "subject": "Science",
                "questions": [
                    {
                        "text": "What planet is known as the Red Planet?",
                        "options": [
                            ("Venus", False),
                            ("Mars", True),
                            ("Jupiter", False),
                            ("Saturn", False),
                        ]
                    },
                    {
                        "text": "What is the chemical symbol for Water?",
                        "options": [
                            ("CO2", False),
                            ("O2", False),
                            ("H2O", True),
                            ("NaCl", False),
                        ]
                    }
                ]
            },
            {
                "subject": "Computer Science",
                "questions": [
                    {
                        "text": "What does CPU stand for?",
                        "options": [
                            ("Central Processing Unit", True),
                            ("Computer Personal Unit", False),
                            ("Central Program Utility", False),
                            ("Control Processing Unit", False),
                        ]
                    },
                    {
                        "text": "Which data structure operates on a Last In First Out (LIFO) principle?",
                        "options": [
                            ("Queue", False),
                            ("Array", False),
                            ("Stack", True),
                            ("Linked List", False),
                        ]
                    }
                ]
            }
        ]

        total_subjects = 0
        total_questions = 0
        total_options = 0

        for s_data in quiz_data:
            subject = Subject.objects.create(name=s_data["subject"])
            total_subjects += 1
            self.stdout.write(f"Created Subject: {subject.name}")

            for q_data in s_data["questions"]:
                question = Question.objects.create(
                    subject=subject,
                    question_text=q_data["text"]
                )
                total_questions += 1
                self.stdout.write(f"  Created Question: {question.question_text}")

                for opt_text, is_ans in q_data["options"]:
                    Option.objects.create(
                        question=question,
                        option_text=opt_text,
                        is_answer=is_ans
                    )
                    total_options += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nSeeding complete:\n"
            f"- Subjects: {total_subjects}\n"
            f"- Questions: {total_questions}\n"
            f"- Options: {total_options} (exactly 1 correct answer per question)"
        ))
