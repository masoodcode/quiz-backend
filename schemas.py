from pydantic import BaseModel
from typing import List


class OptionOut(BaseModel):
    id: int
    text: str

    class Config:
        from_attributes = True


class QuestionOut(BaseModel):
    id: int
    text: str
    options: List[OptionOut]

    class Config:
        from_attributes = True


class AnswerIn(BaseModel):
    question_id: int
    selected_option_id: int


class SubmitIn(BaseModel):
    answers: List[AnswerIn]


class AnswerResult(BaseModel):
    question_id: int
    question_text: str
    selected_option: str
    correct_option: str
    is_correct: bool


class SubmitOut(BaseModel):
    total: int
    score: int
    results: List[AnswerResult]
