from typing import List, Optional, Any

# Import exclusively from the modern Pydantic V2 library.
from pydantic import BaseModel, Field

from .schemas import ProjectStatus, ArticleStatus


# --- API Request/Response Models (Pydantic V2) ---

class ProjectBase(BaseModel):
    name: str
    keyword: str
    base_url: str
    genre: Optional[str] = None
    location: str = "India"


class ProjectCreate(ProjectBase):
    manual_keywords: Optional[List[str]] = Field(
        default=None, description="Optional list of keywords from tools like NeuronWriter"
    )

class Project(ProjectBase):
    id: int
    status: ProjectStatus
    manual_keywords: Optional[List[str]] = None

    class Config:
        from_attributes = True # Use 'from_attributes' for Pydantic V2 ORM mode


class ProjectCreateResponse(Project):
    task_id: str


class TaskCreationResponse(BaseModel):
    task_id: str
    message: str

class Article(BaseModel):
    id: int
    title: str
    content: str
    status: ArticleStatus
    project_id: int
    class Config:
        from_attributes = True

class TaskStatus(BaseModel):
    task_id: str
    task_status: str
    task_result: Optional[Any] = None


# --- AI Structured Output Models (Pydantic V2) ---
# The PydanticOutputParser in the latest LangChain versions works correctly with V2 models.

class TopicCluster(BaseModel):
    cluster_name: str = Field(description="A concise, descriptive name for the topic cluster.")
    headings_and_keywords: List[str] = Field(description="A de-duplicated list of related headings and keywords belonging to this cluster.")

class TopicClusterList(BaseModel):
    clusters: List[TopicCluster]

class H3Subheading(BaseModel):
    h3: str

class H2Section(BaseModel):
    h2: str
    h3s: List[H3Subheading]

class SeoOutline(BaseModel):
    h1: str
    sections: List[H2Section]

