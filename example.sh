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
        "params": {"new_name": "total_cases"}
      }
    ]
  }'



curl -X POST "http://localhost:8001/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [[1.2, 3.4, 5.6, 7.8]],
    "model_version": "latest"
  }'