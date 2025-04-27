import requests
import json
import os
import time
import torch
import torch.nn as nn
import requests

BASE_URL = "http://localhost:8001"
MODELS_DIR = "test_models"
METRICS_DIR = "test_metrics"

# Ensure test directories exist
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(METRICS_DIR, exist_ok=True)

# --- Helper Functions ---
class DummyModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.linear = nn.Linear(4, 1) # Matches config

    def forward(self, x):
        return self.linear(x)

def create_dummy_model_files(version="v_test"):
    """Creates dummy model and config files for testing uploads."""
    model_dir = os.path.join(MODELS_DIR, version)
    os.makedirs(model_dir, exist_ok=True)

    # Create and save a minimal valid TorchScript model
    model_path = os.path.join(model_dir, "model.pt")
    dummy_model = DummyModel()
    dummy_input = torch.randn(1, 4) # Example input matching config
    scripted_model = torch.jit.trace(dummy_model, dummy_input)
    scripted_model.save(model_path)

    # Dummy config file
    config_path = os.path.join(model_dir, "config.json")
    config_data = {"input_features": 4, "output_features": 1, "description": "Dummy test model"}
    with open(config_path, "w") as f:
        json.dump(config_data, f)

    return model_path, config_path

def cleanup_dummy_files(version="v_test"):
    """Removes dummy model files after testing."""
    model_dir = os.path.join(MODELS_DIR, version)
    if os.path.exists(model_dir):
        for filename in os.listdir(model_dir):
            os.remove(os.path.join(model_dir, filename))
        os.rmdir(model_dir)
    # Basic cleanup for metrics, more robust cleanup might be needed
    metrics_file = os.path.join(METRICS_DIR, f"{version}_metrics.json")
    if os.path.exists(metrics_file):
        os.remove(metrics_file)
    predictions_file = os.path.join(METRICS_DIR, f"{version}_predictions.jsonl")
    if os.path.exists(predictions_file):
        os.remove(predictions_file)

# --- Test Functions ---
def test_root():
    print("\n--- Testing Root Endpoint (/) ---")
    try:
        response = requests.get(f"{BASE_URL}/")
        response.raise_for_status()
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return False

def test_list_models():
    print("\n--- Testing List Models Endpoint (/models) ---")
    try:
        response = requests.get(f"{BASE_URL}/models")
        response.raise_for_status()
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.json().get("models", [])
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return []

def test_upload_model(version="v_test"):
    print(f"\n--- Testing Upload Model Endpoint (/models/upload) with version {version} ---")
    model_path, config_path = create_dummy_model_files(version)
    try:
        with open(model_path, 'rb') as mf, open(config_path, 'rb') as cf:
            files = {
                'model_file': (os.path.basename(model_path), mf, 'application/octet-stream'),
                'config_file': (os.path.basename(config_path), cf, 'application/json')
            }
            response = requests.post(f"{BASE_URL}/models/upload?version={version}", files=files)
            response.raise_for_status()
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")
            return True
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        if response is not None:
            print(f"Response Text: {response.text}")
        return False
    finally:
        # Basic cleanup, might leave empty dirs if intermediate steps fail
        # cleanup_dummy_files(version) # Keep files for subsequent tests
        pass

def test_predict(model_version="latest", sample_input=[[1.0, 2.0, 3.0, 4.0]]):
    print(f"\n--- Testing Predict Endpoint (/predict) with version {model_version} ---")
    payload = {"inputs": sample_input, "model_version": model_version}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(f"{BASE_URL}/predict", headers=headers, json=payload)
        response.raise_for_status()
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        if response is not None:
            print(f"Response Text: {response.text}")
        return False

def test_get_metrics(version):
    print(f"\n--- Testing Get Metrics Endpoint (/models/{version}/metrics) ---")
    if not version:
        print("Skipping metrics test: No version specified.")
        return False
    try:
        # Wait a bit for metrics to potentially be generated after prediction
        time.sleep(2)
        response = requests.get(f"{BASE_URL}/models/{version}/metrics")
        response.raise_for_status()
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        if response is not None:
            print(f"Response Text: {response.text}")
        return False

def test_activate_model(version):
    print(f"\n--- Testing Activate Model Endpoint (/models/{version}/activate) ---")
    if not version:
        print("Skipping activation test: No version specified.")
        return False
    try:
        response = requests.post(f"{BASE_URL}/models/{version}/activate")
        response.raise_for_status()
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        if response is not None:
            print(f"Response Text: {response.text}")
        return False

if __name__ == "__main__":
    print("Starting ML Service API Tests...")
    test_version = "v_test_run"

    # 1. Check if API is running
    if not test_root():
        print("API root not accessible. Exiting tests.")
        exit(1)

    # 2. List initial models
    initial_models = test_list_models()

    # 3. Upload a new test model
    upload_success = test_upload_model(test_version)

    # 4. List models again to see the uploaded one
    models_after_upload = test_list_models()
    uploaded_model_found = any(m['version'] == test_version for m in models_after_upload)
    print(f"Uploaded model {test_version} found in list: {uploaded_model_found}")

    # 5. Test prediction (using the uploaded version if successful, else try latest)
    predict_version = test_version if upload_success else "latest"
    # Note: Prediction will likely fail with dummy model. This tests the endpoint call.
    print(f"\nAttempting prediction with version: {predict_version} (expect failure with dummy model)")
    test_predict(model_version=predict_version)

    # 6. Test getting metrics (for the uploaded version if successful)
    if upload_success:
        test_get_metrics(test_version)
    else:
        print("Skipping metrics test as upload failed.")

    # 7. Test activating the uploaded model (if successful)
    if upload_success:
        test_activate_model(test_version)
        # Verify activation by listing models again
        models_after_activation = test_list_models()
        activated_model = next((m for m in models_after_activation if m['version'] == test_version), None)
        if activated_model:
            print(f"Model {test_version} is default after activation: {activated_model.get('is_default')}")
        else:
            print(f"Could not verify activation for model {test_version}")
    else:
        print("Skipping activation test as upload failed.")

    # Cleanup
    print(f"\nCleaning up dummy files for version {test_version}...")
    cleanup_dummy_files(test_version)

    print("\nML Service API Tests Finished.")
