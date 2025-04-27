from pydantic import BaseModel, HttpUrl
from typing import Any, Dict, List, Union
import json

def ensure_serializable(obj: Any) -> Any:
    """Ensure an object is JSON serializable, converting special types when needed."""
    if isinstance(obj, HttpUrl):
        return str(obj)
    elif isinstance(obj, BaseModel):
        return ensure_serializable(obj.dict())
    elif isinstance(obj, dict):
        return {k: ensure_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [ensure_serializable(item) for item in obj]
    elif isinstance(obj, tuple):
        return [ensure_serializable(item) for item in obj]
    elif isinstance(obj, set):
        return [ensure_serializable(item) for item in obj]
    return obj

def serialize_pydantic(model: Union[BaseModel, List[BaseModel], Dict[str, Any]]) -> Dict[str, Any]:
    """Convert Pydantic models to dictionaries that are fully JSON serializable."""
    return ensure_serializable(model)
