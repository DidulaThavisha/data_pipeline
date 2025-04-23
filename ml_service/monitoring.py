import os
import json
import time
import logging
import numpy as np
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error
import threading

logger = logging.getLogger(__name__)

class ModelMonitor:
    def __init__(self, metrics_dir="metrics"):
        self.metrics_dir = metrics_dir
        self.metrics_lock = threading.Lock()
        
        # Create metrics directory if it doesn't exist
        os.makedirs(self.metrics_dir, exist_ok=True)
    
    def log_prediction(self, model_version: str, inputs: List[List[float]], 
                       outputs: List[Any], inference_time: float):
        """Log a prediction for monitoring purposes"""
        try:
            timestamp = datetime.now().isoformat()
            
            log_entry = {
                "timestamp": timestamp,
                "model_version": model_version,
                "inference_time_ms": inference_time,
                "inputs_shape": [len(inputs), len(inputs[0]) if inputs else 0],
                "outputs_shape": [len(outputs), len(outputs[0]) if outputs and isinstance(outputs[0], list) else 0]
            }
            
            # Get the log file path for this model version
            log_file = os.path.join(self.metrics_dir, f"{model_version}_predictions.jsonl")
            
            # Append to log file
            with self.metrics_lock:
                with open(log_file, "a") as f:
                    f.write(json.dumps(log_entry) + "\n")
            
            # Update aggregated metrics
            self._update_metrics(model_version, inference_time)
            
        except Exception as e:
            logger.error(f"Error logging prediction: {str(e)}")
    
    def _update_metrics(self, model_version: str, inference_time: float):
        """Update aggregated metrics for a model version"""
        metrics_file = os.path.join(self.metrics_dir, f"{model_version}_metrics.json")
        
        with self.metrics_lock:
            # Load existing metrics or create new ones
            if os.path.exists(metrics_file):
                with open(metrics_file, "r") as f:
                    metrics = json.load(f)
            else:
                metrics = {
                    "total_predictions": 0,
                    "avg_inference_time_ms": 0,
                    "min_inference_time_ms": float('inf'),
                    "max_inference_time_ms": 0,
                    "last_updated": None
                }
            
            # Update metrics
            n = metrics["total_predictions"]
            metrics["total_predictions"] += 1
            metrics["avg_inference_time_ms"] = (metrics["avg_inference_time_ms"] * n + inference_time) / (n + 1)
            metrics["min_inference_time_ms"] = min(metrics["min_inference_time_ms"], inference_time)
            metrics["max_inference_time_ms"] = max(metrics["max_inference_time_ms"], inference_time)
            metrics["last_updated"] = datetime.now().isoformat()
            
            # Save updated metrics
            with open(metrics_file, "w") as f:
                json.dump(metrics, f, indent=2)
    
    def get_model_metrics(self, model_version: str) -> Dict[str, Any]:
        """Get performance metrics for a specific model version"""
        metrics_file = os.path.join(self.metrics_dir, f"{model_version}_metrics.json")
        
        if not os.path.exists(metrics_file):
            raise FileNotFoundError(f"Metrics for model version {model_version} not found")
        
        with open(metrics_file, "r") as f:
            metrics = json.load(f)
        
        # Add additional analysis if prediction logs are available
        predictions_file = os.path.join(self.metrics_dir, f"{model_version}_predictions.jsonl")
        if os.path.exists(predictions_file):
            # Calculate additional metrics from the prediction logs
            metrics["recent_performance"] = self._analyze_recent_performance(predictions_file)
        
        return metrics
    
    def _analyze_recent_performance(self, predictions_file: str, limit: int = 1000) -> Dict[str, Any]:
        """Analyze the most recent predictions for performance trends"""
        # Read the last N predictions
        predictions = []
        with open(predictions_file, "r") as f:
            for line in f:
                predictions.append(json.loads(line))
                if len(predictions) >= limit:
                    predictions = predictions[-limit:]
        
        if not predictions:
            return {}
        
        # Extract timestamps and inference times
        timestamps = [datetime.fromisoformat(p["timestamp"]) for p in predictions]
        inference_times = [p["inference_time_ms"] for p in predictions]
        
        # Calculate time-based metrics
        recent_avg_time = np.mean(inference_times[-100:]) if len(inference_times) >= 100 else np.mean(inference_times)
        
        # Check for performance degradation
        is_slowing = False
        if len(inference_times) >= 200:
            recent_100 = np.mean(inference_times[-100:])
            previous_100 = np.mean(inference_times[-200:-100])
            is_slowing = recent_100 > previous_100 * 1.1  # 10% slowdown
        
        return {
            "recent_predictions_count": len(predictions),
            "recent_avg_inference_time_ms": recent_avg_time,
            "performance_degradation_detected": is_slowing,
            "last_prediction_time": timestamps[-1].isoformat() if timestamps else None
        }
    
    def detect_data_drift(self, model_version: str, reference_data: List[List[float]], 
                         current_data: List[List[float]]) -> Dict[str, Any]:
        """
        Detect data drift by comparing current data distribution to reference data
        
        Args:
            model_version: The model version
            reference_data: The reference data used to train the model
            current_data: The current input data
            
        Returns:
            Dictionary with drift metrics
        """
        try:
            # Convert to numpy arrays
            ref_data = np.array(reference_data)
            curr_data = np.array(current_data)
            
            # Basic statistical drift detection
            ref_mean = np.mean(ref_data, axis=0)
            curr_mean = np.mean(curr_data, axis=0)
            
            ref_std = np.std(ref_data, axis=0)
            curr_std = np.std(curr_data, axis=0)
            
            # Calculate drift metrics
            mean_drift = np.abs(ref_mean - curr_mean) / (ref_std + 1e-10)  # Normalized mean difference
            std_ratio = curr_std / (ref_std + 1e-10)  # Ratio of standard deviations
            
            # Calculate drift score (higher score means more drift)
            drift_score = np.mean(mean_drift)
            
            # Determine if drift is significant
            is_significant = drift_score > 0.5 or np.any(std_ratio > 2.0) or np.any(std_ratio < 0.5)
            
            return {
                "model_version": model_version,
                "drift_score": float(drift_score),
                "mean_drift": mean_drift.tolist(),
                "std_ratio": std_ratio.tolist(),
                "is_significant": is_significant,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating data drift: {str(e)}")
            return {"error": str(e)}
