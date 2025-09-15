# main.py

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy.orm import Session
from .database import create_db_and_tables, get_db
from . import crud, models, schemas
from .tasks import generate_outline_task
from .tasks import generate_outline_task, generate_full_article_task

from celery.result import AsyncResult
from .celery_config import celery_app

# Initialize Database and tables
create_db_and_tables()

app = FastAPI(title="SEO AI AGENT", version="1.0.0")


@app.get("/", tags=["Root"])
async def read_root():
    return {"status": "ok", "message": "Welcome to the SEO AI AGENT API"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows all origins for simplicity in development
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods
    allow_headers=["*"], # Allows all headers
)

@app.post("/projects/", response_model=models.ProjectCreateResponse, tags=["Projects"])
def create_new_project(
    project: models.ProjectCreate, db: Session = Depends(get_db)
):
    db_project = crud.create_project(db=db, project=project)
    
    # Pass the manual_keywords to the background task
    task = generate_outline_task.delay(
        project_id=db_project.id, 
        keyword=db_project.keyword,
        manual_keywords=db_project.manual_keywords
    )
    
    # Use the .from_orm compatibility mode to create the response model
    response_data = models.Project.model_validate(db_project)
    return models.ProjectCreateResponse(**response_data.model_dump(), task_id=task.id)

@app.get("/tasks/{task_id}", response_model=models.TaskStatus, tags=["Tasks"])
def get_task_status(task_id: str):
    """Polls the status of a Celery task."""
    task_result = AsyncResult(task_id, app=celery_app)
    result = {
        "task_id": task_id,
        "task_status": task_result.status,
        "task_result": task_result.result if task_result.ready() else None
    }
    return result

@app.get("/projects/{project_id}/article", response_model=models.Article, tags=["Articles"])
def get_article_for_project(project_id: int, db: Session = Depends(get_db)):
    """Retrieves the first article associated with a given project."""
    article = crud.get_article_by_project_id(db, project_id=project_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found for this project.")
    return article

@app.post("/articles/{article_id}/generate", response_model=models.TaskCreationResponse, tags=["Articles"])
def generate_article_endpoint(article_id: int):
    """
    Triggers the asynchronous generation of a full article draft from an outline.
    """
    task = generate_full_article_task.delay(article_id)
    return {"task_id": task.id, "message": "Article generation process started."}

