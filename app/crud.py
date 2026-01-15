from sqlalchemy.orm import Session
from app.models import OCRData

def save_ocr_data(db: Session, data: dict):
    record = OCRData(**data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
