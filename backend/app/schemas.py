import enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Enum,
    Text,
    JSON  
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ProjectStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class ArticleStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    keyword = Column(String, index=True, nullable=False)
    base_url = Column(String, nullable=False)
    genre = Column(String, nullable=True)
    location = Column(String, nullable=True, default="India")
    manual_keywords = Column(JSON, nullable=True) # <-- ADD THIS COLUMN
    status = Column(Enum(ProjectStatus), default=ProjectStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    articles = relationship("Article", back_populates="project")

class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=True) # Will store the final outline as a JSON string
    status = Column(Enum(ArticleStatus), default=ArticleStatus.DRAFT, nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    project = relationship("Project", back_populates="articles")

class ArticleStatus(str, enum.Enum):
    DRAFT = "DRAFT"  # The initial state, meaning an outline exists
    WRITING_IN_PROGRESS = "WRITING_IN_PROGRESS"
    DRAFT_COMPLETE = "DRAFT_COMPLETE" # The full first draft is written
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"