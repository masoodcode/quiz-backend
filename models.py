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
