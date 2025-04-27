from fastapi import FastAPI, HTTPException, File, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import torch
import time

import os
import logging
from datetime import datetime
import numpy as np
from starlette.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Histogram

from model_loader import ModelManager
from monitoring import ModelMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("model_server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="ML Model Serving API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize model manager and monitoring
model_manager = ModelManager()
model_monitor = ModelMonitor()

# --- Prometheus Metrics ---
# Create a registry for Prometheus metrics
registry = CollectorRegistry()
# Example custom metrics (you can add more specific ones)
request_counter = Counter("api_requests_total", "Total number of API requests", ["endpoint", "method", "status_code"], registry=registry)
prediction_latency = Histogram("api_prediction_latency_seconds", "Latency of predictions", ["model_version"], registry=registry)
# --------------------------

class PredictionRequest(BaseModel):
    inputs: List[List[float]]
    model_version: Optional[str] = "latest"

class PredictionResponse(BaseModel):
    predictions: List[Any]
    model_version: str
    inference_time_ms: float

@app.on_event("startup")
async def startup_event():
    """Load models on startup"""
    model_manager.load_models()

@app.get("/")
async def root():
    request_counter.labels(endpoint="/", method="GET", status_code=200).inc() # Example metric increment
    return {"message": "ML Model Serving API is running"}

# --- Add Prometheus Metrics Endpoint ---
@app.get("/metrics")
async def metrics():
    """Expose Prometheus metrics."""
    return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)
# -------------------------------------

@app.get("/models")
async def list_models():
    """List all available model versions"""
    return {"models": model_manager.list_available_models()}

@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest, background_tasks: BackgroundTasks):
    """Make predictions using the specified model version"""
    status_code = 500 # Default to error
    model_version_label = "unknown"
    start_timer = time.time() # Use time.time for latency calculation
    try:
        # Get the model
        model, model_version = model_manager.get_model(request.model_version)
        model_version_label = model_version # Set label for metrics

        # Convert inputs to tensor
        inputs = torch.tensor(request.inputs, dtype=torch.float32)

        # Record start time (for application logic, keep using datetime if needed elsewhere)
        start_time_dt = datetime.now()

        # Run inference
        with torch.no_grad():
            outputs = model(inputs).numpy().tolist()

        # Calculate inference time (for application logic)
        inference_time_ms = (datetime.now() - start_time_dt).total_seconds() * 1000

        # Log prediction asynchronously
        background_tasks.add_task(
            model_monitor.log_prediction,
            model_version,
            request.inputs,
            outputs,
            inference_time_ms
        )

        status_code = 200 # Set status code for success
        response_data = {
            "predictions": outputs,
            "model_version": model_version,
            "inference_time_ms": inference_time_ms
        }
        # Record latency metric on success
        latency = time.time() - start_timer
        prediction_latency.labels(model_version=model_version_label).observe(latency)
        return response_data

    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        # Ensure status_code remains 500 or set appropriately
        status_code = 500 # Or map specific exceptions to other codes
        raise HTTPException(status_code=status_code, detail=str(e))
    finally:
        # Increment request counter regardless of success/failure
        request_counter.labels(endpoint="/predict", method="POST", status_code=status_code).inc()

@app.post("/models/upload")
async def upload_model(
    model_file: UploadFile = File(...),
    config_file: UploadFile = File(...),
    version: Optional[str] = None
):
    """Upload a new model version"""
    try:
        # Generate version if not provided
        if not version:
            version = f"v{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create model directory
        model_dir = os.path.join(model_manager.models_dir, version)
        os.makedirs(model_dir, exist_ok=True)
        
        # Save model file
        model_path = os.path.join(model_dir, "model.pt")
        with open(model_path, "wb") as f:
            f.write(await model_file.read())
        
        # Save config file
        config_path = os.path.join(model_dir, "config.json")
        with open(config_path, "wb") as f:
            f.write(await config_file.read())
        
        # Reload models
        model_manager.load_models()
        
        return {"message": f"Model version {version} uploaded successfully"}
    
    except Exception as e:
        logger.error(f"Model upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models/{version}/metrics")
async def get_model_metrics(version: str):
    """Get performance metrics for a specific model version"""
    try:
        metrics = model_monitor.get_model_metrics(version)
        return metrics
    except Exception as e:
        logger.error(f"Error getting metrics: {str(e)}")
        raise HTTPException(status_code=404, detail=f"Metrics for model version {version} not found")

@app.post("/models/{version}/activate")
async def activate_model(version: str):
    """Set a specific model version as the default (latest)"""
    try:
        model_manager.set_default_model(version)
        return {"message": f"Model version {version} is now the default"}
    except Exception as e:
        logger.error(f"Error activating model: {str(e)}")
        raise HTTPException(status_code=404, detail=f"Model version {version} not found")

if __name__ == "__main__":
    import uvicorn
    import time
    uvicorn.run("model_server:app", host="0.0.0.0", port=8001, reload=True)
