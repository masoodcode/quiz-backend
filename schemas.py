from pydantic import BaseModel
from typing import List, Optional


# ─────────────────────────────────────────────
# OUTPUT schemas (what the API sends back)
# ─────────────────────────────────────────────

class OptionOut(BaseModel):
    id:   int
    text: str
    # is_correct is intentionally hidden from GET responses

    class Config:
        from_attributes = True


class QuestionOut(BaseModel):
    id:      int
    text:    str
    options: List[OptionOut]

    class Config:
        from_attributes = True


class TopicOut(BaseModel):
    id:             int
    name:           str
    question_count: int = 0
    image_url:      Optional[str] = None   # Cloudinary URL — None if no study image

    class Config:
        from_attributes = True


class CategoryOut(BaseModel):
    id:          int
    name:        str
    icon:        str
    color:       str
    topic_count: int = 0

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# INPUT schemas (what the API receives — admin)
# ─────────────────────────────────────────────

class OptionIn(BaseModel):
    text:       str
    is_correct: bool


class QuestionIn(BaseModel):
    topic_id: int
    text:     str
    options:  List[OptionIn]


class TopicIn(BaseModel):
    category_id: int
    name:        str


class CategoryIn(BaseModel):
    name:  str
    icon:  str = "📚"
    color: str = "#6C63FF"


# ─────────────────────────────────────────────
# SUBMIT schemas (quiz submission)
# ─────────────────────────────────────────────

class AnswerIn(BaseModel):
    question_id:        int
    selected_option_id: int


class SubmitIn(BaseModel):
    answers: List[AnswerIn]


class AnswerResult(BaseModel):
    question_id:     int
    question_text:   str
    selected_option: str
    correct_option:  str
    is_correct:      bool


class SubmitOut(BaseModel):
    total:   int
    score:   int
    results: List[AnswerResult]


# ─────────────────────────────────────────────
# BULK schemas (admin bulk question upload)
# ─────────────────────────────────────────────

class BulkQuestionResult(BaseModel):
    index:   int     # position in the submitted list (0-based)
    success: bool
    text:    str     # question text for reference
    id:      int = 0 # question id if created successfully
    error:   str = "" # error message if failed


class BulkUploadOut(BaseModel):
    total:    int
    created:  int
    failed:   int
    results:  List[BulkQuestionResult]
