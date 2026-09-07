import os
import random
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.orm import Session
from typing import List

from database import engine, get_db, Base
from models import Category, Topic, Question, Option
from schemas import (
    CategoryOut, CategoryIn,
    TopicOut, TopicIn,
    QuestionOut, QuestionIn,
    SubmitIn, SubmitOut, AnswerResult,
)
from seed import seed

# ── Startup ──────────────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)
seed()

app = FastAPI(title="Quiz API", version="2.0")

# ── CORS — allow Flutter web/app to call the API ─────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Key protection for admin (write) endpoints ───────────────────────────
API_KEY        = os.getenv("QUIZ_API_KEY", "changeme-set-in-env")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(key: str = Security(api_key_header)):
    if key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    return key


# ═════════════════════════════════════════════════════════════════════════════
# PUBLIC endpoints — Flutter uses these
# ═════════════════════════════════════════════════════════════════════════════

@app.get("/")
def root():
    return {"message": "Quiz API v2 is running"}


@app.get("/categories", response_model=List[CategoryOut])
def get_categories(db: Session = Depends(get_db)):
    """Return all categories with topic count."""
    categories = db.query(Category).all()
    result = []
    for cat in categories:
        result.append(CategoryOut(
            id=cat.id,
            name=cat.name,
            icon=cat.icon,
            color=cat.color,
            topic_count=len(cat.topics),
        ))
    return result


@app.get("/categories/{category_id}/topics", response_model=List[TopicOut])
def get_topics(category_id: int, db: Session = Depends(get_db)):
    """Return all topics for a category with question count."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    result = []
    for topic in category.topics:
        result.append(TopicOut(
            id=topic.id,
            name=topic.name,
            question_count=len(topic.questions),
        ))
    return result


@app.get("/topics/{topic_id}/questions", response_model=List[QuestionOut])
def get_questions(
    topic_id: int,
    limit: int = 0,          # 0 = return all, N = return N random questions
    db: Session = Depends(get_db),
):
    """Return questions for a topic — randomized order, options shuffled too."""
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    questions = list(topic.questions)

    # Randomly select N questions if limit is set
    if limit and limit < len(questions):
        questions = random.sample(questions, limit)
    else:
        random.shuffle(questions)

    result = []
    for q in questions:
        # Shuffle options so correct answer isn't always in same position
        options = list(q.options)
        random.shuffle(options)
        result.append(QuestionOut(
            id=q.id,
            text=q.text,
            options=[{"id": o.id, "text": o.text} for o in options],
        ))
    return result


@app.post("/submit", response_model=SubmitOut)
def submit_answers(payload: SubmitIn, db: Session = Depends(get_db)):
    """Submit answers and get score with detailed results."""
    results = []
    score   = 0

    for answer in payload.answers:
        question = db.query(Question).filter(
            Question.id == answer.question_id
        ).first()
        if not question:
            raise HTTPException(
                status_code=404,
                detail=f"Question {answer.question_id} not found"
            )

        selected = db.query(Option).filter(
            Option.id == answer.selected_option_id
        ).first()
        if not selected:
            raise HTTPException(
                status_code=404,
                detail=f"Option {answer.selected_option_id} not found"
            )

        correct = next((o for o in question.options if o.is_correct), None)
        if selected.is_correct:
            score += 1

        results.append(AnswerResult(
            question_id=question.id,
            question_text=question.text,
            selected_option=selected.text,
            correct_option=correct.text if correct else "",
            is_correct=selected.is_correct,
        ))

    return SubmitOut(total=len(payload.answers), score=score, results=results)


# ═════════════════════════════════════════════════════════════════════════════
# ADMIN endpoints — protected by API key, used via Postman
# ═════════════════════════════════════════════════════════════════════════════

@app.post("/admin/categories", response_model=CategoryOut)
def create_category(
    payload: CategoryIn,
    db: Session = Depends(get_db),
    _: str = Depends(require_api_key),
):
    """Create a new category (e.g. AWS Cloud Practitioner, Docker)."""
    existing = db.query(Category).filter(Category.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")

    cat = Category(name=payload.name, icon=payload.icon, color=payload.color)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return CategoryOut(id=cat.id, name=cat.name, icon=cat.icon,
                       color=cat.color, topic_count=0)


@app.post("/admin/topics", response_model=TopicOut)
def create_topic(
    payload: TopicIn,
    db: Session = Depends(get_db),
    _: str = Depends(require_api_key),
):
    """Create a new topic under a category."""
    category = db.query(Category).filter(
        Category.id == payload.category_id
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    topic = Topic(name=payload.name, category_id=payload.category_id)
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return TopicOut(id=topic.id, name=topic.name, question_count=0)


@app.post("/admin/questions", response_model=QuestionOut)
def create_question(
    payload: QuestionIn,
    db: Session = Depends(get_db),
    _: str = Depends(require_api_key),
):
    """Add a question with options under a topic."""
    topic = db.query(Topic).filter(Topic.id == payload.topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    if len(payload.options) < 2:
        raise HTTPException(
            status_code=400, detail="At least 2 options required"
        )

    correct_count = sum(1 for o in payload.options if o.is_correct)
    if correct_count != 1:
        raise HTTPException(
            status_code=400, detail="Exactly one option must be correct"
        )

    question = Question(text=payload.text, topic_id=payload.topic_id)
    db.add(question)
    db.flush()

    for opt in payload.options:
        db.add(Option(
            text=opt.text,
            is_correct=opt.is_correct,
            question_id=question.id,
        ))

    db.commit()
    db.refresh(question)

    return QuestionOut(
        id=question.id,
        text=question.text,
        options=[{"id": o.id, "text": o.text} for o in question.options],
    )


@app.delete("/admin/questions/{question_id}")
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(require_api_key),
):
    """Delete a question and its options."""
    question = db.query(Question).filter(
        Question.id == question_id
    ).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    db.delete(question)
    db.commit()
    return {"message": f"Question {question_id} deleted"}
