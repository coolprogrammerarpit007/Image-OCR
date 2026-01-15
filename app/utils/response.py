from typing import Any, Optional

def success_response(message: str, data: Any = None):
    return {
        "status": True,
        "message": message,
        "data": data
    }

def error_response(message: str, error: Optional[str] = None):
    return {
        "status": False,
        "message": message,
        "error": error
    }
