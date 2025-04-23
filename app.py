from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import os

from models import ProcessedData, DataRequest
from database import get_db, engine, Base, init_db
import schemas
from data_ingestion import start_ingestion_job

# Initialize FastAPI app
app = FastAPI(title="Data Processing API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables on startup
@app.on_event("startup")
async def startup_db_client():
    # Print environment values for debugging
    print(f"DATABASE_URL: {os.getenv('DATABASE_URL', 'Not set')}")
    print(f"REDIS_URL: {os.getenv('REDIS_URL', 'Not set')}")
    
    # Initialize database
    init_db()

@app.get("/", response_model=dict)
async def root():
    return {"message": "Data Processing API is running"}

@app.post("/ingest", response_model=schemas.JobResponse)
async def ingest_data(request: schemas.DataIngestionRequest):
    """Start a new data ingestion job."""
    job_id = start_ingestion_job(request.sources, request.transformation_rules)
    return {"job_id": job_id, "status": "processing"}

@app.get("/jobs/{job_id}", response_model=schemas.JobStatus)
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Get the status of a data ingestion job."""
    # Query the database for the job status
    job = db.query(DataRequest).filter(DataRequest.id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found")
    
    return {
        "job_id": job_id, 
        "status": job.status, 
        "records_processed": job.records_processed,
        "error_message": job.error_message
    }

@app.get("/data", response_model=List[schemas.ProcessedDataResponse])
async def get_data(
    category: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Retrieve processed data with optional filtering."""
    query = db.query(ProcessedData)
    
    if category:
        query = query.filter(ProcessedData.category == category)
    
    result = query.limit(limit).offset(offset).all()
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
