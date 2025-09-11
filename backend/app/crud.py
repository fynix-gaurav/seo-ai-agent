from sqlalchemy.orm import Session
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