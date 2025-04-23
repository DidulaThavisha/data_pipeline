from pydantic import BaseModel, HttpUrl
from typing import List, Dict, Any, Optional
from datetime import datetime

class DataSource(BaseModel):
    source_type: str  # "rest" or "graphql"
    url: HttpUrl
    headers: Optional[Dict[str, str]] = None
    query: Optional[str] = None  # For GraphQL
    params: Optional[Dict[str, Any]] = None  # For REST

class TransformationRule(BaseModel):
    field: str
    operation: str  # "rename", "filter", "aggregate", etc.
    params: Dict[str, Any]

class DataIngestionRequest(BaseModel):
    sources: List[DataSource]
    transformation_rules: Optional[List[TransformationRule]] = None

class JobResponse(BaseModel):
    job_id: str
    status: str

class JobStatus(BaseModel):
    job_id: str
    status: str
    records_processed: Optional[int] = None
    error_message: Optional[str] = None

class ProcessedDataResponse(BaseModel):
    id: int
    source: str
    category: str
    data: Dict[str, Any]
    created_at: datetime
    
    class Config:
        orm_mode = True
