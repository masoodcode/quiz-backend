import os
import random
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.orm import Session
from typing import List

from database import engine, get_db, Base
from models import (
    Category, Topic, Question, Option,
    DiagramTopic, Diagram, DiagramNode, DiagramEdge,
    YamlTopic, YamlExercise, YamlBlank,
)
from schemas import (
    CategoryOut, CategoryIn,
    TopicOut, TopicIn,
    QuestionOut, QuestionIn,
    SubmitIn, SubmitOut, AnswerResult,
    BulkUploadOut, BulkQuestionResult,
    OralQuestionOut, OralJudgeIn, OralJudgeOut,
    DiagramTopicOut, DiagramTopicIn,
    DiagramOut, DiagramSummaryOut, DiagramIn,
    DiagramNodeOut, DiagramEdgeOut,
    YamlTopicOut, YamlTopicIn,
    YamlExerciseOut, YamlExerciseSummaryOut, YamlExerciseIn,
    YamlJudgeIn, YamlJudgeOut,
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


# ── Feature flag: randomize MCQ question + option order ──────────────────────
# Default OFF so questions appear in a stable, repeatable order (good while
# first learning the material). Flip RANDOMIZE=true in the environment to
# restore shuffling later — no code change needed.
RANDOMIZE = os.getenv("RANDOMIZE", "false").lower() == "true"


# ── OpenAI client (for the AI Oral Exam feature) ─────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


def get_openai_client():
    """Lazily create the OpenAI client so the app still boots if the key
    is missing (the oral endpoints will just return a clear error)."""
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="OpenAI API key not configured on the server",
        )
    from openai import OpenAI
    return OpenAI(api_key=OPENAI_API_KEY)


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
            image_url=topic.image_url,
        ))
    return result


@app.get("/topics/{topic_id}/questions", response_model=List[QuestionOut])
def get_questions(
    topic_id: int,
    limit: int = 0,          # 0 = return all, N = return N random questions
    db: Session = Depends(get_db),
):
    """Return questions for a topic.

    When RANDOMIZE is on, both question order and option order are shuffled.
    When off (default), everything is returned in a stable order (by id) so
    the same topic shows the same sequence every time — useful while first
    learning the material.
    """
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    questions = list(topic.questions)

    if RANDOMIZE:
        # Randomly select N questions if limit is set, else shuffle all
        if limit and limit < len(questions):
            questions = random.sample(questions, limit)
        else:
            random.shuffle(questions)
    else:
        # Stable, repeatable order
        questions.sort(key=lambda q: q.id)
        if limit:
            questions = questions[:limit]

    result = []
    for q in questions:
        options = list(q.options)
        if RANDOMIZE:
            # Shuffle options so correct answer isn't always in same position
            random.shuffle(options)
        else:
            options.sort(key=lambda o: o.id)
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
# ORAL EXAM endpoints — voice Q&A judged by OpenAI
# ═════════════════════════════════════════════════════════════════════════════

@app.get("/topics/{topic_id}/oral-questions", response_model=List[OralQuestionOut])
def get_oral_questions(
    topic_id: int,
    limit: int = 5,          # default 5 questions for an oral round
    db: Session = Depends(get_db),
):
    """Return questions for oral exam. Each includes the correct answer text
    (from the MCQ correct option) so it can serve as the reference answer
    when the AI judges the student's spoken response."""
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    questions = list(topic.questions)
    if limit and limit < len(questions):
        questions = random.sample(questions, limit)
    else:
        random.shuffle(questions)

    result = []
    for q in questions:
        correct = next((o for o in q.options if o.is_correct), None)
        result.append(OralQuestionOut(
            id=q.id,
            text=q.text,
            reference_answer=correct.text if correct else "",
        ))
    return result


@app.post("/oral/judge", response_model=OralJudgeOut)
def judge_oral_answer(payload: OralJudgeIn):
    """Use OpenAI to judge a student's spoken answer against the reference
    answer, like a teacher grading an oral exam. Returns correctness, a score,
    short feedback, and an ideal answer."""
    client = get_openai_client()

    system_prompt = (
        "You are a friendly but rigorous examiner conducting an oral exam on "
        "Kubernetes and DevOps. A student answers questions by speaking, and their "
        "speech is transcribed (so expect minor transcription errors — judge on "
        "meaning, not exact wording). "
        "You are given the question, a reference answer, and the student's answer. "
        "Decide if the student's answer is essentially correct. Be fair: accept "
        "answers that capture the core idea even if phrased differently or "
        "incomplete on minor details. Reject answers that are wrong, empty, or "
        "miss the main concept. "
        "Reply with a JSON object ONLY, with these exact keys: "
        '"is_correct" (boolean), "score" (integer 0-100 for accuracy/completeness), '
        '"feedback" (one or two warm, encouraging sentences addressed directly to '
        'the student, spoken-style, mentioning what was right or what was missing), '
        'and "ideal_answer" (a concise 1-2 sentence model answer).'
    )

    user_prompt = (
        f"Question: {payload.question}\n\n"
        f"Reference answer: {payload.reference_answer}\n\n"
        f"Student's answer: {payload.user_answer}"
    )

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        import json
        raw = completion.choices[0].message.content
        data = json.loads(raw)
        return OralJudgeOut(
            is_correct=bool(data.get("is_correct", False)),
            score=int(data.get("score", 0)),
            feedback=str(data.get("feedback", "")),
            ideal_answer=str(data.get("ideal_answer", payload.reference_answer)),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI judging failed: {e}")


# ═════════════════════════════════════════════════════════════════════════════
# DIAGRAM FILL endpoints — fill-in-the-blank concept diagrams (separate feature)
# ═════════════════════════════════════════════════════════════════════════════

import random as _random


@app.get("/diagram-topics", response_model=List[DiagramTopicOut])
def get_diagram_topics(db: Session = Depends(get_db)):
    """List all diagram topics with how many diagrams each has."""
    topics = db.query(DiagramTopic).all()
    return [
        DiagramTopicOut(
            id=t.id, name=t.name, icon=t.icon, color=t.color,
            diagram_count=len(t.diagrams),
        )
        for t in topics
    ]


@app.get("/diagram-topics/{topic_id}/diagrams",
         response_model=List[DiagramSummaryOut])
def get_diagrams_for_topic(topic_id: int, db: Session = Depends(get_db)):
    """List diagrams in a topic (summary only)."""
    topic = db.query(DiagramTopic).filter(DiagramTopic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Diagram topic not found")
    return [
        DiagramSummaryOut(
            id=d.id, title=d.title, layout=d.layout,
            blank_count=sum(1 for n in d.nodes if n.is_blank),
        )
        for d in topic.diagrams
    ]


@app.get("/diagrams/{diagram_id}", response_model=DiagramOut)
def get_diagram(diagram_id: int, db: Session = Depends(get_db)):
    """Fetch one diagram ready to render. Blank node labels are hidden;
    a shuffled word bank (correct blanks + distractors) and an answers map
    are returned so the app can let the user drag-and-grade on-device."""
    d = db.query(Diagram).filter(Diagram.id == diagram_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Diagram not found")

    nodes_out    = []
    answers      = {}
    explanations = {}
    blank_labels = []
    for n in d.nodes:
        if n.is_blank:
            answers[str(n.node_key)] = n.label
            blank_labels.append(n.label)
        if n.explanation:
            explanations[str(n.node_key)] = n.explanation
        nodes_out.append(DiagramNodeOut(
            node_key=n.node_key,
            label="" if n.is_blank else n.label,
            is_blank=n.is_blank,
            shape=n.shape,
            position=n.position,
            branch=n.branch,
        ))

    edges_out = [
        DiagramEdgeOut(from_key=e.from_key, to_key=e.to_key,
                       branch_label=e.branch_label)
        for e in d.edges
    ]

    distractors = [x.strip() for x in (d.distractors or "").split(",")
                   if x.strip()]
    word_bank = blank_labels + distractors
    _random.shuffle(word_bank)

    return DiagramOut(
        id=d.id,
        title=d.title,
        instruction=d.instruction,
        layout=d.layout,
        nodes=nodes_out,
        edges=edges_out,
        word_bank=word_bank,
        answers=answers,
        explanations=explanations,
    )


@app.post("/admin/diagram-topics", response_model=DiagramTopicOut)
def create_diagram_topic(
    payload: DiagramTopicIn,
    db: Session = Depends(get_db),
    _: str = Depends(require_api_key),
):
    existing = db.query(DiagramTopic).filter(
        DiagramTopic.name == payload.name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Topic already exists")
    t = DiagramTopic(name=payload.name, icon=payload.icon, color=payload.color)
    db.add(t)
    db.commit()
    db.refresh(t)
    return DiagramTopicOut(id=t.id, name=t.name, icon=t.icon,
                           color=t.color, diagram_count=0)


@app.post("/admin/diagrams", response_model=DiagramOut)
def create_diagram(
    payload: DiagramIn,
    db: Session = Depends(get_db),
    _: str = Depends(require_api_key),
):
    """Create a diagram. Auto-creates the diagram topic by name if needed."""
    if len(payload.nodes) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 nodes")
    if not any(n.is_blank for n in payload.nodes):
        raise HTTPException(status_code=400,
                            detail="At least one node must be a blank")

    # Get or create the topic
    topic = db.query(DiagramTopic).filter(
        DiagramTopic.name == payload.topic_name
    ).first()
    if not topic:
        topic = DiagramTopic(name=payload.topic_name)
        db.add(topic)
        db.flush()

    diagram = Diagram(
        title=payload.title,
        instruction=payload.instruction,
        layout=payload.layout,
        distractors=",".join(payload.distractors),
        topic_id=topic.id,
    )
    db.add(diagram)
    db.flush()

    for n in payload.nodes:
        db.add(DiagramNode(
            diagram_id=diagram.id,
            node_key=n.node_key,
            label=n.label,
            is_blank=n.is_blank,
            shape=n.shape,
            position=n.position,
            branch=n.branch,
            explanation=n.explanation,
        ))
    for e in payload.edges:
        db.add(DiagramEdge(
            diagram_id=diagram.id,
            from_key=e.from_key,
            to_key=e.to_key,
            branch_label=e.branch_label,
        ))

    db.commit()
    db.refresh(diagram)
    return get_diagram(diagram.id, db)


@app.delete("/admin/diagrams/{diagram_id}")
def delete_diagram(
    diagram_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(require_api_key),
):
    d = db.query(Diagram).filter(Diagram.id == diagram_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Diagram not found")
    db.delete(d)
    db.commit()
    return {"message": f"Diagram {diagram_id} deleted"}


# ═════════════════════════════════════════════════════════════════════════════
# YAML PRACTICE endpoints — fill-in-the-blank + AI-graded write (separate feature)
# ═════════════════════════════════════════════════════════════════════════════

@app.get("/yaml-topics", response_model=List[YamlTopicOut])
def get_yaml_topics(db: Session = Depends(get_db)):
    topics = db.query(YamlTopic).all()
    return [
        YamlTopicOut(id=t.id, name=t.name, icon=t.icon, color=t.color,
                     exercise_count=len(t.exercises))
        for t in topics
    ]


@app.get("/yaml-topics/{topic_id}/exercises",
         response_model=List[YamlExerciseSummaryOut])
def get_yaml_exercises(topic_id: int, db: Session = Depends(get_db)):
    topic = db.query(YamlTopic).filter(YamlTopic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="YAML topic not found")
    return [
        YamlExerciseSummaryOut(
            id=e.id, title=e.title, mode=e.mode, blank_count=len(e.blanks)
        )
        for e in topic.exercises
    ]


@app.get("/yaml-exercises/{exercise_id}", response_model=YamlExerciseOut)
def get_yaml_exercise(exercise_id: int, db: Session = Depends(get_db)):
    e = db.query(YamlExercise).filter(YamlExercise.id == exercise_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="YAML exercise not found")

    if e.mode == "write":
        return YamlExerciseOut(
            id=e.id, title=e.title, mode=e.mode, task_prompt=e.task_prompt,
        )

    # fill mode — build word bank + answers/explanations maps
    answers      = {}
    explanations = {}
    answer_vals  = []
    for b in e.blanks:
        answers[str(b.position)] = b.answer
        answer_vals.append(b.answer)
        if b.explanation:
            explanations[str(b.position)] = b.explanation

    distractors = [x.strip() for x in (e.distractors or "").split(",")
                   if x.strip()]
    # de-dup while keeping order, then shuffle
    seen = set()
    word_bank = []
    for w in answer_vals + distractors:
        if w not in seen:
            seen.add(w)
            word_bank.append(w)
    _random.shuffle(word_bank)

    return YamlExerciseOut(
        id=e.id, title=e.title, mode=e.mode,
        template=e.template, word_bank=word_bank,
        answers=answers, explanations=explanations,
    )


@app.post("/yaml/judge", response_model=YamlJudgeOut)
def judge_yaml(payload: YamlJudgeIn, db: Session = Depends(get_db)):
    """Use OpenAI to grade a user-written manifest. The task prompt and
    reference manifest are looked up server-side so the answer is never
    exposed to the client."""
    ex = db.query(YamlExercise).filter(
        YamlExercise.id == payload.exercise_id
    ).first()
    if not ex or ex.mode != "write":
        raise HTTPException(status_code=404,
                            detail="Write-mode YAML exercise not found")

    client = get_openai_client()

    system_prompt = (
        "You are a Kubernetes and Istio YAML examiner. Given a task, a "
        "reference manifest, and a student's manifest, judge whether the "
        "student's YAML correctly accomplishes the task. Accept valid "
        "variations (field order, quoting, equivalent values, extra harmless "
        "fields). Focus on: correct apiVersion/kind, required spec fields, and "
        "the values that matter for the task. Minor style differences are fine. "
        "Reply with JSON ONLY with keys: "
        '"is_correct" (boolean), "score" (integer 0-100), '
        '"feedback" (one or two encouraging sentences to the student), '
        'and "issues" (array of short strings naming any concrete mistakes; '
        "empty if none)."
    )
    user_prompt = (
        f"Task: {ex.task_prompt}\n\n"
        f"Reference manifest:\n{ex.reference_yaml}\n\n"
        f"Student's manifest:\n{payload.user_yaml}"
    )

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        import json
        data = json.loads(completion.choices[0].message.content)
        return YamlJudgeOut(
            is_correct=bool(data.get("is_correct", False)),
            score=int(data.get("score", 0)),
            feedback=str(data.get("feedback", "")),
            issues=[str(x) for x in data.get("issues", [])],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI judging failed: {e}")


@app.post("/admin/yaml-topics", response_model=YamlTopicOut)
def create_yaml_topic(
    payload: YamlTopicIn,
    db: Session = Depends(get_db),
    _: str = Depends(require_api_key),
):
    existing = db.query(YamlTopic).filter(YamlTopic.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Topic already exists")
    t = YamlTopic(name=payload.name, icon=payload.icon, color=payload.color)
    db.add(t)
    db.commit()
    db.refresh(t)
    return YamlTopicOut(id=t.id, name=t.name, icon=t.icon,
                        color=t.color, exercise_count=0)


@app.post("/admin/yaml-exercises", response_model=YamlExerciseSummaryOut)
def create_yaml_exercise(
    payload: YamlExerciseIn,
    db: Session = Depends(get_db),
    _: str = Depends(require_api_key),
):
    if payload.mode not in ("fill", "write"):
        raise HTTPException(status_code=400, detail="mode must be fill or write")
    if payload.mode == "fill" and (not payload.template or not payload.blanks):
        raise HTTPException(status_code=400,
                            detail="fill mode needs a template and blanks")
    if payload.mode == "write" and (not payload.task_prompt
                                    or not payload.reference_yaml):
        raise HTTPException(status_code=400,
                            detail="write mode needs task_prompt and reference_yaml")

    topic = db.query(YamlTopic).filter(
        YamlTopic.name == payload.topic_name
    ).first()
    if not topic:
        topic = YamlTopic(name=payload.topic_name)
        db.add(topic)
        db.flush()

    ex = YamlExercise(
        topic_id=topic.id,
        title=payload.title,
        mode=payload.mode,
        template=payload.template,
        distractors=",".join(payload.distractors),
        task_prompt=payload.task_prompt,
        reference_yaml=payload.reference_yaml,
    )
    db.add(ex)
    db.flush()

    for b in payload.blanks:
        db.add(YamlBlank(
            exercise_id=ex.id,
            position=b.position,
            answer=b.answer,
            explanation=b.explanation,
        ))
    db.commit()
    db.refresh(ex)
    return YamlExerciseSummaryOut(
        id=ex.id, title=ex.title, mode=ex.mode, blank_count=len(ex.blanks)
    )


@app.delete("/admin/yaml-exercises/{exercise_id}")
def delete_yaml_exercise(
    exercise_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(require_api_key),
):
    e = db.query(YamlExercise).filter(YamlExercise.id == exercise_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="YAML exercise not found")
    db.delete(e)
    db.commit()
    return {"message": f"YAML exercise {exercise_id} deleted"}


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
    return TopicOut(id=topic.id, name=topic.name, question_count=0, image_url=None)


@app.patch("/admin/topics/{topic_id}/image")
def set_topic_image(
    topic_id: int,
    image_url: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_api_key),
):
    """Set or update the study image URL for a topic."""
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    topic.image_url = image_url
    db.commit()
    return {"message": f"Image set for topic '{topic.name}'", "image_url": image_url}


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


@app.post("/admin/questions/bulk", response_model=BulkUploadOut)
def create_questions_bulk(
    payload: List[QuestionIn],
    db: Session = Depends(get_db),
    _: str = Depends(require_api_key),
):
    """Add multiple questions in one request.
    Each question is validated individually.
    If one fails, the rest still get processed.
    Returns a summary of created vs failed.
    """
    results      = []
    created_count = 0
    failed_count  = 0

    for i, q_data in enumerate(payload):
        try:
            # Validate topic exists
            topic = db.query(Topic).filter(Topic.id == q_data.topic_id).first()
            if not topic:
                raise ValueError(f"Topic {q_data.topic_id} not found")

            # Validate options
            if len(q_data.options) < 2:
                raise ValueError("At least 2 options required")

            correct_count = sum(1 for o in q_data.options if o.is_correct)
            if correct_count != 1:
                raise ValueError("Exactly one option must be correct")

            # Insert question
            question = Question(text=q_data.text, topic_id=q_data.topic_id)
            db.add(question)
            db.flush()

            for opt in q_data.options:
                db.add(Option(
                    text=opt.text,
                    is_correct=opt.is_correct,
                    question_id=question.id,
                ))

            db.flush()
            created_count += 1
            results.append(BulkQuestionResult(
                index=i,
                success=True,
                text=q_data.text,
                id=question.id,
            ))

        except Exception as e:
            # One failure doesn't stop the rest
            db.rollback()
            failed_count += 1
            results.append(BulkQuestionResult(
                index=i,
                success=False,
                text=q_data.text,
                error=str(e),
            ))

    db.commit()

    return BulkUploadOut(
        total=len(payload),
        created=created_count,
        failed=failed_count,
        results=results,
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


@app.delete("/admin/topics/{topic_id}")
def delete_topic(
    topic_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(require_api_key),
):
    """Delete a topic and all its questions/options (cascade)."""
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    name = topic.name
    db.delete(topic)
    db.commit()
    return {"message": f"Topic '{name}' and all its questions deleted"}


@app.delete("/admin/categories/{category_id}/topics")
def delete_all_topics_in_category(
    category_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(require_api_key),
):
    """Delete ALL topics (and their questions/options) under a category.
    Use this to clean up and start fresh for a category.
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    topics = db.query(Topic).filter(Topic.category_id == category_id).all()
    count  = len(topics)
    for topic in topics:
        db.delete(topic)
    db.commit()
    return {
        "message":       f"Deleted {count} topics and all their questions from '{category.name}'",
        "topics_deleted": count,
    }
