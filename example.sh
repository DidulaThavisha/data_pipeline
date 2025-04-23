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


