from database import engine, SessionLocal, Base
from models import Question, Option

quiz_data = [
    {
        "text": "What is the capital of France?",
        "options": [
            {"text": "Berlin", "is_correct": False},
            {"text": "Madrid", "is_correct": False},
            {"text": "Paris", "is_correct": True},
            {"text": "Rome", "is_correct": False},
        ],
    },
    {
        "text": "Which planet is known as the Red Planet?",
        "options": [
            {"text": "Earth", "is_correct": False},
            {"text": "Mars", "is_correct": True},
            {"text": "Jupiter", "is_correct": False},
            {"text": "Saturn", "is_correct": False},
        ],
    },
    {
        "text": "What is 2 + 2?",
        "options": [
            {"text": "3", "is_correct": False},
            {"text": "4", "is_correct": True},
            {"text": "5", "is_correct": False},
            {"text": "6", "is_correct": False},
        ],
    },
    {
        "text": "Which language is used to build Flutter apps?",
        "options": [
            {"text": "Kotlin", "is_correct": False},
            {"text": "Swift", "is_correct": False},
            {"text": "Dart", "is_correct": True},
            {"text": "Java", "is_correct": False},
        ],
    },
    {
        "text": "What does HTTP stand for?",
        "options": [
            {"text": "HyperText Transfer Protocol", "is_correct": True},
            {"text": "High Transfer Text Protocol", "is_correct": False},
            {"text": "HyperText Transmission Process", "is_correct": False},
            {"text": "Hybrid Text Transfer Protocol", "is_correct": False},
        ],
    },
]


def seed():
    """Create tables (if they don't exist) and insert seed data."""
    # Create all tables defined in models.py
    # Safe to call multiple times — skips tables that already exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if already seeded to avoid duplicates
        if db.query(Question).count() > 0:
            print("Database already seeded. Skipping.")
            return

        for q_data in quiz_data:
            question = Question(text=q_data["text"])
            db.add(question)
            db.flush()  # flush to get the auto-generated question.id

            for opt in q_data["options"]:
                option = Option(
                    text=opt["text"],
                    is_correct=opt["is_correct"],
                    question_id=question.id,
                )
                db.add(option)

        db.commit()
        print(f"Seeded {len(quiz_data)} questions successfully.")

    except Exception as e:
        db.rollback()
        print(f"Seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
