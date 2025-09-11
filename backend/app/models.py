from pydantic import BaseModel, Field
from typing import Optional, List
from .schemas import ProjectStatus

# --- API Request/Response Models ---

class ProjectBase(BaseModel):
    name: str
    keyword: str
    base_url: str
    genre: Optional[str] = None
    location: str = "India"

class ProjectCreate(ProjectBase):
    manual_keywords: Optional[List[str]] = Field(default=None, description="Optional list of keywords from tools like NeuronWriter")

class Project(ProjectBase):
    id: int
    status: ProjectStatus
    manual_keywords: Optional[List[str]] = None
    class Config:
        from_attributes = True

class ProjectCreateResponse(Project):
    task_id: str

# --- AI Structured Output Models ---

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