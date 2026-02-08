from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Union
from uuid import UUID


def sanitize_for_json(data: Any) -> Any:
    """Recursively sanitize data for JSON serialization.
    
    Converts datetime objects to ISO strings, handles LangChain messages,
    Pydantic models, Enums, and other common non-serializable types.
    
    Args:
        data: The data to sanitize
        
    Returns:
        JSON-serializable version of the data
    """
    # Handle None
    if data is None:
        return None

    # Handle basic types that are already serializable
    if isinstance(data, (str, int, float, bool)):
        return data

    # Handle datetime, date, time
    if isinstance(data, (datetime, date, time)):
        return data.isoformat()

    # Handle UUID and Decimal
    if isinstance(data, (UUID, Decimal)):
        return str(data)

    # Handle Enum
    if isinstance(data, Enum):
        return data.value

    # Handle LangChain messages (they often have a .dict() or .to_json() or are objects)
    if hasattr(data, "to_json") and callable(data.to_json):
        try:
            # Some LangChain objects have to_json
            return sanitize_for_json(data.to_json())
        except Exception:
            pass

    # Handle Pydantic models or objects with .dict() / .model_dump()
    if hasattr(data, "model_dump") and callable(data.model_dump):
        return sanitize_for_json(data.model_dump())
    elif hasattr(data, "dict") and callable(data.dict):
        return sanitize_for_json(data.dict())

    # Handle dicts (recursive)
    if isinstance(data, dict):
        return {str(k): sanitize_for_json(v) for k, v in data.items()}

    # Handle lists, tuples, sets (recursive)
    if isinstance(data, (list, tuple, set)):
        return [sanitize_for_json(item) for item in data]

    # Handle objects with __dict__ (custom classes)
    if hasattr(data, "__dict__"):
        try:
            return sanitize_for_json(data.__dict__)
        except Exception:
            pass

    # Fallback to string representation for anything else
    # This ensures we don't break the whole serialization process
    try:
        return str(data)
    except Exception:
        return repr(data)

