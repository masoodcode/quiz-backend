from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database import Base


class Category(Base):
    __tablename__ = "categories"

    id    = Column(Integer, primary_key=True, index=True)
    name  = Column(String, nullable=False, unique=True)
    icon  = Column(String, nullable=False, default="📚")   # emoji icon
    color = Column(String, nullable=False, default="#6C63FF")  # hex color

    topics = relationship("Topic", back_populates="category", cascade="all, delete")


class Topic(Base):
    __tablename__ = "topics"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    image_url   = Column(String, nullable=True)   # Cloudinary URL for study image

    category  = relationship("Category", back_populates="topics")
    questions = relationship("Question", back_populates="topic", cascade="all, delete")


class Question(Base):
    __tablename__ = "questions"

    id       = Column(Integer, primary_key=True, index=True)
    text     = Column(String, nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)

    topic   = relationship("Topic", back_populates="questions")
    options = relationship("Option", back_populates="question", cascade="all, delete")


class Option(Base):
    __tablename__ = "options"

    id          = Column(Integer, primary_key=True, index=True)
    text        = Column(String, nullable=False)
    is_correct  = Column(Boolean, default=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)

    question = relationship("Question", back_populates="options")


# ═════════════════════════════════════════════════════════════════════════════
# DIAGRAM FILL feature — fully separate from the quiz tables above.
# A DiagramTopic groups diagrams (e.g. "Istio Traffic Management").
# A Diagram is a flow/flowchart made of nodes + edges. Some nodes are blanks
# the student must fill by dragging the right word from a shuffled word bank.
# ═════════════════════════════════════════════════════════════════════════════

class DiagramTopic(Base):
    __tablename__ = "diagram_topics"

    id    = Column(Integer, primary_key=True, index=True)
    name  = Column(String, nullable=False, unique=True)
    icon  = Column(String, nullable=False, default="🧩")
    color = Column(String, nullable=False, default="#2E7D32")  # green theme

    diagrams = relationship(
        "Diagram", back_populates="topic", cascade="all, delete"
    )


class Diagram(Base):
    __tablename__ = "diagrams"

    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String, nullable=False)
    instruction = Column(String, nullable=False,
                         default="Drag the right word into each blank box")
    # "linear"  = top-to-bottom chain of boxes
    # "flowchart" = one decision diamond with two branches
    layout      = Column(String, nullable=False, default="linear")
    # Comma-separated wrong-answer words added to the word bank
    distractors = Column(String, nullable=True)
    topic_id    = Column(Integer, ForeignKey("diagram_topics.id"), nullable=False)

    topic = relationship("DiagramTopic", back_populates="diagrams")
    nodes = relationship(
        "DiagramNode", back_populates="diagram",
        cascade="all, delete", order_by="DiagramNode.position",
    )
    edges = relationship(
        "DiagramEdge", back_populates="diagram", cascade="all, delete"
    )


class DiagramNode(Base):
    __tablename__ = "diagram_nodes"

    id         = Column(Integer, primary_key=True, index=True)
    diagram_id = Column(Integer, ForeignKey("diagrams.id"), nullable=False)
    # node_key is a per-diagram identifier used by edges (e.g. 1, 2, 3...)
    node_key   = Column(Integer, nullable=False)
    label      = Column(String, nullable=False)   # the correct answer when blank
    is_blank   = Column(Boolean, default=False)
    # short "why" shown after checking — turns a guess into a mini-lesson
    explanation = Column(String, nullable=True)
    # shape: "process" (rectangle), "start" (oval), "end" (oval), "decision" (diamond)
    shape      = Column(String, nullable=False, default="process")
    # position orders nodes top-to-bottom
    position   = Column(Integer, nullable=False, default=0)
    # branch: for flowcharts — "left" or "right" places a node under a decision;
    # None means it sits on the main vertical line
    branch     = Column(String, nullable=True)

    diagram = relationship("Diagram", back_populates="nodes")


class DiagramEdge(Base):
    __tablename__ = "diagram_edges"

    id           = Column(Integer, primary_key=True, index=True)
    diagram_id   = Column(Integer, ForeignKey("diagrams.id"), nullable=False)
    from_key     = Column(Integer, nullable=False)
    to_key       = Column(Integer, nullable=False)
    # optional label shown on the arrow, e.g. "Yes" / "No" for decisions
    branch_label = Column(String, nullable=True)

    diagram = relationship("Diagram", back_populates="edges")


# ═════════════════════════════════════════════════════════════════════════════
# YAML PRACTICE feature — separate from quiz/diagram tables.
# Two modes:
#   "fill"  = a manifest with ___1___, ___2___ placeholders the user fills
#             (deterministic grading against stored answers)
#   "write" = a task prompt; the user writes a full manifest, graded by AI
#             against a reference manifest
# ═════════════════════════════════════════════════════════════════════════════

class YamlTopic(Base):
    __tablename__ = "yaml_topics"

    id    = Column(Integer, primary_key=True, index=True)
    name  = Column(String, nullable=False, unique=True)
    icon  = Column(String, nullable=False, default="📄")
    color = Column(String, nullable=False, default="#B8860B")  # amber/gold
    # Group heading for the app (e.g. "Traffic Management", "Security")
    section = Column(String, nullable=True, default="General")

    exercises = relationship(
        "YamlExercise", back_populates="topic", cascade="all, delete"
    )


class YamlExercise(Base):
    __tablename__ = "yaml_exercises"

    id       = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("yaml_topics.id"), nullable=False)
    title    = Column(String, nullable=False)
    mode     = Column(String, nullable=False, default="fill")  # fill | write

    # ── fill mode ──
    # The manifest text containing ___1___, ___2___ ... placeholders.
    template    = Column(String, nullable=True)
    # Comma-separated distractor words added to the word bank.
    distractors = Column(String, nullable=True)

    # ── write mode ──
    task_prompt   = Column(String, nullable=True)  # what to build
    reference_yaml = Column(String, nullable=True)  # model answer for AI judge

    topic  = relationship("YamlTopic", back_populates="exercises")
    blanks = relationship(
        "YamlBlank", back_populates="exercise",
        cascade="all, delete", order_by="YamlBlank.position",
    )


class YamlBlank(Base):
    __tablename__ = "yaml_blanks"

    id          = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(Integer, ForeignKey("yaml_exercises.id"), nullable=False)
    # position matches the placeholder number (1 -> ___1___)
    position    = Column(Integer, nullable=False)
    answer      = Column(String, nullable=False)   # the correct value
    explanation = Column(String, nullable=True)    # shown after checking

    exercise = relationship("YamlExercise", back_populates="blanks")
