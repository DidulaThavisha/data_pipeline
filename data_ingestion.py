import uuid
import requests
import logging
from celery import Celery
from typing import List, Dict, Any
import json
import os
import datetime

from database import SessionLocal
from models import DataRequest, ProcessedData
from utils import serialize_pydantic

# Get Redis URL from environment or use default
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Configure Celery with the Redis URL from environment variable
celery = Celery(
    'data_pipeline',
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data_ingestion.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def start_ingestion_job(sources, transformation_rules=None):
    """Start a new data ingestion job and return the job ID."""
    job_id = str(uuid.uuid4())
    
    # Store the job request in the database
    db = SessionLocal()
    try:
        request = DataRequest(id=job_id, status="pending")
        db.add(request)
        db.commit()
    finally:
        db.close()
    
    # Convert Pydantic models to serializable dictionaries
    serializable_sources = serialize_pydantic(sources)
    serializable_transformation_rules = serialize_pydantic(transformation_rules) if transformation_rules else None
    
    # Start the Celery task asynchronously
    process_data.delay(job_id, serializable_sources, serializable_transformation_rules)
    
    return job_id, request

@celery.task(bind=True, max_retries=3)
def process_data(self, job_id, sources, transformation_rules=None):
    """Process data from multiple sources and apply transformations."""
    db = SessionLocal()
    try:
        # Update job status to processing
        request = db.query(DataRequest).filter(DataRequest.id == job_id).first()
        if not request:
            logger.error(f"Job ID {job_id} not found")
            return
        
        logger.info(f"Processing job {job_id} with sources: {sources}")
        request.status = "processing"

        db.commit()
        
        records_processed = 0
        
        # Process each data source
        for source in sources:
            try:
                # Fetch data based on source type
                logger.info(f"Fetching data from {source['url']}")
                if source["source_type"] == "rest":
                    data = fetch_rest_data(source["url"], source.get("headers"), source.get("params"))
                elif source["source_type"] == "graphql":
                    data = fetch_graphql_data(source["url"], source.get("query"), source.get("headers"))
                else:
                    logger.warning(f"Unsupported source type: {source['source_type']}")
                    continue
                request.status = "before_transformation"
                # Apply transformations
                if transformation_rules:
                    data = apply_transformations(data, transformation_rules)
                
                # Store processed data
                store_processed_data(db, job_id, source["source_type"], data)
                
                records_processed += len(data) if isinstance(data, list) else 1
                
            except Exception as e:
                logger.error(f"Error processing source {source['url']}: {str(e)}")
                # Retry the task if there's an error
                self.retry(exc=e, countdown=30)
        
        # Update job status to completed
        request.status = "completed"
        request.records_processed = records_processed
        request.completed_at = datetime.datetime.utcnow()  # Add completion timestamp
        db.commit()
        
        logger.info(f"Job {job_id} completed. Processed {records_processed} records.")
        
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {str(e)}")
        request.status = "failed"
        request.error_message = str(e)
        db.commit()
    
    finally:
        db.close()

def fetch_rest_data(url, headers=None, params=None):
    """Fetch data from a REST API."""
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching REST data from {url}: {str(e)}")
        raise

def fetch_graphql_data(url, query, headers=None):
    """Fetch data from a GraphQL API."""
    try:
        response = requests.post(
            url,
            json={"query": query},
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching GraphQL data from {url}: {str(e)}")
        raise

def apply_transformations(data, transformation_rules):
    """Apply transformation rules to the data."""
    # This is a simplified implementation
    transformed_data = data
    
    for rule in transformation_rules:
        field = rule["field"]
        operation = rule["operation"]
        params = rule["params"]
        
        # Example transformations
        if operation == "rename":
            transformed_data = rename_field(transformed_data, field, params["new_name"])
        elif operation == "filter":
            transformed_data = filter_data(transformed_data, field, params["condition"])
        
    return transformed_data

def rename_field(data, old_field, new_field):
    """Rename a field in the data."""
    # Implementation for lists of dictionaries
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and old_field in item:
                item[new_field] = item.pop(old_field)
    # Implementation for a single dictionary
    elif isinstance(data, dict) and old_field in data:
        data[new_field] = data.pop(old_field)
    
    return data

def filter_data(data, field, condition):
    """Filter data based on a condition."""
    # Only process if data is a list
    if not isinstance(data, list):
        return data
    
    filtered_data = []
    condition_op = condition.get("operator", "eq")
    condition_value = condition.get("value")
    
    for item in data:
        if not isinstance(item, dict) or field not in item:
            continue
            
        field_value = item[field]
        
        # Apply the appropriate comparison
        include_item = False
        if condition_op == "eq":
            include_item = field_value == condition_value
        elif condition_op == "neq":
            include_item = field_value != condition_value
        elif condition_op == "gt":
            include_item = field_value > condition_value
        elif condition_op == "lt":
            include_item = field_value < condition_value
        elif condition_op == "contains":
            include_item = condition_value in field_value
        
        if include_item:
            filtered_data.append(item)
    
    return filtered_data

def store_processed_data(db, job_id, source, data):
    """Store processed data in the database."""
    # For list data, insert each item
    if isinstance(data, list):
        for item in data:
            processed_data = ProcessedData(
                request_id=job_id,
                source=source,
                category=item.get("category", "uncategorized"),
                data=item
            )
            db.add(processed_data)
    else:
        # For single item data
        processed_data = ProcessedData(
            request_id=job_id,
            source=source,
            category=data.get("category", "uncategorized"),
            data=data
        )
        db.add(processed_data)
    
    db.commit()
