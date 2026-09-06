from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from database import engine, get_db, Base
from models import Question, Option
from schemas import QuestionOut, SubmitIn, SubmitOut, AnswerResult
from seed import seed

# Create tables and seed data on startup
Base.metadata.create_all(bind=engine)
seed()

app = FastAPI(title="Quiz API")

# Allow Flutter web/app to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Quiz API is running"}


@app.get("/questions", response_model=List[QuestionOut])
def get_all_questions(db: Session = Depends(get_db)):
    """Return all questions with their options (correct answer hidden)."""
    questions = db.query(Question).all()
    return questions


@app.get("/questions/{question_id}", response_model=QuestionOut)
def get_question(question_id: int, db: Session = Depends(get_db)):
    """Return a single question by ID."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@app.post("/submit", response_model=SubmitOut)
def submit_answers(payload: SubmitIn, db: Session = Depends(get_db)):
    """Submit answers and get the score with detailed results."""
    results = []
    score = 0

    for answer in payload.answers:
        question = db.query(Question).filter(Question.id == answer.question_id).first()
        if not question:
            raise HTTPException(
                status_code=404,
                detail=f"Question {answer.question_id} not found"
            )

        selected = db.query(Option).filter(Option.id == answer.selected_option_id).first()
        if not selected:
            raise HTTPException(
                status_code=404,
                detail=f"Option {answer.selected_option_id} not found"
            )

        correct = next((o for o in question.options if o.is_correct), None)
        is_correct = selected.is_correct

        if is_correct:
            score += 1

        results.append(AnswerResult(
            question_id=question.id,
            question_text=question.text,
            selected_option=selected.text,
            correct_option=correct.text if correct else "",
            is_correct=is_correct,
        ))

    return SubmitOut(total=len(payload.answers), score=score, results=results)
