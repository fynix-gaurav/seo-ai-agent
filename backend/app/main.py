from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from .database import create_db_and_tables, get_db
from . import crud, models, schemas
from .tasks import generate_outline_task

create_db_and_tables()

app = FastAPI(title="SEO AI AGENT", version="1.0.0")

@app.get("/", tags=["Root"])
async def read_root():
    return {"status": "ok", "message": "Welcome to the SEO AI AGENT API"}

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