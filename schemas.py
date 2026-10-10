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


# ─────────────────────────────────────────────
# ORAL EXAM schemas (voice Q&A, AI judged)
# ─────────────────────────────────────────────

class OralQuestionOut(BaseModel):
    """A question for oral exam — includes the reference (correct) answer text
    so the app can send it to the judge endpoint."""
    id:              int
    text:            str
    reference_answer: str   # the correct MCQ option text — used as the model answer

    class Config:
        from_attributes = True


class OralJudgeIn(BaseModel):
    question:         str    # the question that was asked
    reference_answer: str    # the known correct answer (from MCQ option)
    user_answer:      str    # what the student said (transcribed by speech-to-text)


class OralJudgeOut(BaseModel):
    is_correct: bool    # did the student get it right?
    score:      int     # 0-100 how complete/accurate the answer was
    feedback:   str     # short spoken-style feedback, like a teacher
    ideal_answer: str   # a concise model answer for the student to learn from


# ─────────────────────────────────────────────
# DIAGRAM FILL schemas (fill-in-the-blank diagrams)
# ─────────────────────────────────────────────

# ---- OUTPUT (what the app receives) ----

class DiagramTopicOut(BaseModel):
    id:             int
    name:           str
    icon:           str
    color:          str
    diagram_count:  int = 0

    class Config:
        from_attributes = True


class DiagramNodeOut(BaseModel):
    """A node as the app sees it. For blank nodes the correct label is NOT
    sent — the app only knows it's a blank. 'answer' is returned only when
    the client explicitly needs it for grading on-device."""
    node_key: int
    label:    str      # empty string "" when is_blank (hidden)
    is_blank: bool
    shape:    str
    position: int
    branch:   Optional[str] = None

    class Config:
        from_attributes = True


class DiagramEdgeOut(BaseModel):
    from_key:     int
    to_key:       int
    branch_label: Optional[str] = None

    class Config:
        from_attributes = True


class DiagramOut(BaseModel):
    id:          int
    title:       str
    instruction: str
    layout:      str
    nodes:       List[DiagramNodeOut]
    edges:       List[DiagramEdgeOut]
    word_bank:   List[str]   # shuffled: correct blank labels + distractors
    # answers maps node_key -> correct label, used by the app to grade locally
    answers:     dict
    # explanations maps node_key -> short "why" text, shown after checking
    explanations: dict = {}

    class Config:
        from_attributes = True


class DiagramSummaryOut(BaseModel):
    """Lightweight listing of a diagram (no nodes/edges)."""
    id:          int
    title:       str
    layout:      str
    blank_count: int = 0

    class Config:
        from_attributes = True


# ---- INPUT (admin create) ----

class DiagramNodeIn(BaseModel):
    node_key:    int
    label:       str
    is_blank:    bool = False
    shape:       str = "process"      # process | start | end | decision
    position:    int = 0
    branch:      Optional[str] = None # left | right | None
    explanation: Optional[str] = None # short "why" shown after checking


class DiagramEdgeIn(BaseModel):
    from_key:     int
    to_key:       int
    branch_label: Optional[str] = None


class DiagramIn(BaseModel):
    topic_name:  str               # auto-creates the diagram topic if new
    title:       str
    instruction: str = "Drag the right word into each blank box"
    layout:      str = "linear"    # linear | flowchart
    distractors: List[str] = []
    nodes:       List[DiagramNodeIn]
    edges:       List[DiagramEdgeIn]


class DiagramTopicIn(BaseModel):
    name:  str
    icon:  str = "🧩"
    color: str = "#2E7D32"
