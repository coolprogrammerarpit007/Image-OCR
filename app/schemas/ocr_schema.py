from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime

class OCRResponse(BaseModel):
    id: int
    filename: str
    document_type: str
    extracted_data: Dict[str, Any]
    confidence_score: float
    created_at: datetime