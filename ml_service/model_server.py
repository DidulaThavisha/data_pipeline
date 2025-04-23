from fastapi import FastAPI, HTTPException, File, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import torch
import json
import os
import logging
from datetime import datetime
import numpy as np

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
    return {"message": "ML Model Serving API is running"}

@app.get("/models")
async def list_models():
    """List all available model versions"""
    return {"models": model_manager.list_available_models()}

@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest, background_tasks: BackgroundTasks):
    """Make predictions using the specified model version"""
    try:
        # Get the model
        model, model_version = model_manager.get_model(request.model_version)
        
        # Convert inputs to tensor
        inputs = torch.tensor(request.inputs, dtype=torch.float32)
        
        # Record start time
        start_time = datetime.now()
        
        # Run inference
        with torch.no_grad():
            outputs = model(inputs).numpy().tolist()
        
        # Calculate inference time
        inference_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Log prediction asynchronously
        background_tasks.add_task(
            model_monitor.log_prediction,
            model_version,
            request.inputs,
            outputs,
            inference_time
        )
        
        return {
            "predictions": outputs,
            "model_version": model_version,
            "inference_time_ms": inference_time
        }
    
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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
    uvicorn.run("model_server:app", host="0.0.0.0", port=8001, reload=True)
