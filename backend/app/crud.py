# crud.py

from sqlalchemy.orm import Session
from typing import List, Optional
from . import models, schemas

def create_project(db: Session, project: models.ProjectCreate) -> schemas.Project:
    db_project = schemas.Project(
        name=project.name,
        keyword=project.keyword,
        base_url=project.base_url,
        genre=project.genre,
        location=project.location,
        manual_keywords=project.manual_keywords # <-- ADD THIS LINE
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

def update_project_status(db: Session, project_id: int, status: schemas.ProjectStatus) -> schemas.Project:
    db_project = db.query(schemas.Project).filter(schemas.Project.id == project_id).first()
    if db_project:
        db_project.status = status
        db.commit()
        db.refresh(db_project)
    return db_project

def create_article_for_project(db: Session, title: str, content: str, project_id: int) -> schemas.Article:
    db_article = schemas.Article(
        title=title,
        content=content,
        project_id=project_id
    )
    db.add(db_article)
    db.commit()
    db.refresh(db_article)
    return db_article

def get_article(db: Session, article_id: int) -> Optional[schemas.Article]:
    """Retrieves an article by its ID."""
    return db.query(schemas.Article).filter(schemas.Article.id == article_id).first()


def update_article_content(
    db: Session, article_id: int, content: str, status: schemas.ArticleStatus
) -> schemas.Article:
    """Updates the content and status of an article."""
    db_article = get_article(db, article_id)
    if db_article:
        db_article.content = content
        db_article.status = status
        db.commit()
        db.refresh(db_article)
    return db_article


def get_article_by_project_id(db: Session, project_id: int) -> Optional[schemas.Article]:
    """Retrieves the first article associated with a project ID."""
    return db.query(schemas.Article).filter(schemas.Article.project_id == project_id).first()