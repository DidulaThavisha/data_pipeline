import os
import json
import torch
import logging
from typing import Dict, Tuple, List, Any
import glob

logger = logging.getLogger(__name__)

class ModelManager:
    def __init__(self, models_dir="models"):
        self.models_dir = models_dir
        self.models = {}  # Dictionary to store loaded models
        self.default_model_version = None
        
        # Create models directory if it doesn't exist
        os.makedirs(self.models_dir, exist_ok=True)
    
    def load_models(self):
        """Load all available model versions"""
        logger.info("Loading model versions...")
        
        # Find all model directories
        model_dirs = glob.glob(os.path.join(self.models_dir, "*"))
        
        # Clear current models
        self.models = {}
        
        if not model_dirs:
            logger.warning("No model versions found")
            return
        
        # Load each model
        for model_dir in model_dirs:
            version = os.path.basename(model_dir)
            try:
                # Load model configuration
                config_path = os.path.join(model_dir, "config.json")
                with open(config_path, "r") as f:
                    config = json.load(f)
                
                # Load model weights
                model_path = os.path.join(model_dir, "model.pt")
                model = torch.jit.load(model_path)
                model.eval()  # Set model to evaluation mode
                
                # Store model and config
                self.models[version] = {
                    "model": model,
                    "config": config
                }
                
                logger.info(f"Loaded model version: {version}")
            
            except Exception as e:
                logger.error(f"Error loading model version {version}: {str(e)}")
        
        # Set default model to the latest version if not already set
        if not self.default_model_version or self.default_model_version not in self.models:
            # Sort versions and get the latest
            versions = sorted(self.models.keys())
            if versions:
                self.default_model_version = versions[-1]
                logger.info(f"Set default model version to: {self.default_model_version}")
    
    def get_model(self, version="latest") -> Tuple[Any, str]:
        """Get a specific model version or the latest one"""
        if not self.models:
            raise ValueError("No models available. Please add models first.")
        
        if version == "latest":
            version = self.default_model_version
        
        if version not in self.models:
            raise ValueError(f"Model version {version} not found")
        
        return self.models[version]["model"], version
    
    def list_available_models(self) -> List[Dict[str, Any]]:
        """List all available model versions with their details"""
        result = []
        
        for version, data in self.models.items():
            result.append({
                "version": version,
                "is_default": version == self.default_model_version,
                "config": data["config"]
            })
        
        return result
    
    def set_default_model(self, version: str):
        """Set a specific model version as the default"""
        if version not in self.models:
            raise ValueError(f"Model version {version} not found")
        
        self.default_model_version = version
        logger.info(f"Set default model version to: {version}")
