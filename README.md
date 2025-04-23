# Data Processing Pipeline & ML Model Serving

This project consists of two main components:
1. A scalable data processing pipeline for ingesting and transforming data from various API sources
2. A machine learning model serving system for deploying and managing PyTorch models

## System Architecture

### Data Processing Pipeline
- **FastAPI** - REST API for ingesting data and retrieving results
- **Celery** - Distributed task queue for asynchronous data processing
- **Redis** - Message broker for Celery and result storage
- **PostgreSQL** - Persistent storage for processed data

### ML Model Serving
- **FastAPI** - REST API for serving ML model predictions
- **PyTorch** - Machine learning framework for model inference
- **Prometheus/Grafana** - Monitoring and visualization for model performance

## Prerequisites

- Docker and Docker Compose
- Python 3.10+
- PostgreSQL (if running locally)
- Redis (if running locally)

## Quick Start

### Using Docker Compose (Recommended)

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd c:\Users\Didula\Desktop\Projects\data_pipeline2
   ```

2. Build and start the services:
   ```bash
   docker-compose up -d
   ```

3. The following services will be available:
   - Data Processing API: http://localhost:8000
   - ML Model Serving API: http://localhost:8001
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3000

### Running Locally (Development)

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up environment variables:
   ```bash
   export DATABASE_URL=postgresql://postgres:postgres@localhost/data_pipeline
   export REDIS_URL=redis://localhost:6379/0
   ```

3. Start the API:
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8000 --reload
   ```

4. In a separate terminal, start the Celery worker:
   ```bash
   celery -A data_ingestion.celery_app worker --loglevel=info
   ```

## Using the Data Processing API

### Ingesting Data

```bash
curl -X POST "http://localhost:8000/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": [
      {
        "source_type": "rest",
        "url": "https://disease.sh/v3/covid-19/countries",
        "headers": {}
      }
    ],
    "transformation_rules": [
      {
        "field": "cases",
        "operation": "rename",
        "params": { "new_name": "total_cases" }
      }
    ]
  }'
```


### Checking Job Status

```bash
curl -X GET "http://localhost:8000/jobs/{job_id}"
```

Replace `{job_id}` with the job ID returned from the ingest request.

### Getting Processed Data

```bash
curl -X GET "http://localhost:8000/data?category=uncategorized&limit=10"
```

## Using the ML Model API

### Uploading a Model

```bash
curl -X POST "http://localhost:8001/models/upload" \
  -F "model_file=@./my_model.pt" \
  -F "config_file=@./config.json" \
  -F "version=v1"
```

### Making Predictions

```bash
curl -X POST "http://localhost:8001/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [[1.0, 2.0, 3.0, 4.0]],
    "model_version": "latest"
  }'
```

### Viewing Model Metrics

```bash
curl -X GET "http://localhost:8001/models/v1/metrics"
```

## Project Structure

```
c:\Users\Didula\Desktop\Projects\data_pipeline2\
├── app.py                  # Main FastAPI application for data processing
├── data_ingestion.py       # Data ingestion and transformation logic
├── database.py             # Database connection and session management
├── models.py               # SQLAlchemy models for the database
├── schemas.py              # Pydantic models for API validation
├── utils.py                # Utility functions including serialization helpers
├── Dockerfile              # Docker configuration for the services
├── docker-compose.yml      # Docker Compose configuration
├── requirements.txt        # Python dependencies
├── entrypoint.sh           # Docker entrypoint script
├── wait-for-db.sh          # Script to wait for database readiness
│
├── ml_service/             # ML Model Serving Component
│   ├── model_server.py     # FastAPI application for model serving
│   ├── model_loader.py     # Model loading and versioning logic
│   ├── monitoring.py       # Model monitoring and metrics collection
│   ├── Dockerfile          # Docker configuration for ML service
│   ├── docker-compose.yml  # Docker Compose for ML service
│   ├── requirements.txt    # Python dependencies for ML service
│   ├── prometheus.yml      # Prometheus configuration
│   └── .github/workflows/  # CI/CD pipeline configuration
```

## Error Handling

If you encounter any errors:

1. Check the logs:
   ```bash
   docker-compose logs api
   docker-compose logs worker
   ```

2. Ensure Redis and PostgreSQL are running:
   ```bash
   docker-compose ps
   ```

3. Verify that the database tables were created:
   ```bash
   docker-compose exec db psql -U postgres -d data_pipeline -c "\dt"
   ```

## Development and Production Considerations

### Development
- Use the `--reload` flag with uvicorn for hot reloading
- Set `DEBUG=True` in your environment for more detailed logs

### Production
- Configure proper SSL/TLS for API endpoints
- Set up monitoring with Prometheus/Grafana
- Implement rate limiting for API endpoints
- Configure database connection pooling properly
- Set up high availability with multiple replicas

## Security Considerations

- API keys or JWT authentication should be implemented for production
- Database credentials should be securely stored using environment variables or secret management services
- Input validation is performed through Pydantic models to prevent injection attacks
- CORS is configured but should be restricted to specific origins in production
