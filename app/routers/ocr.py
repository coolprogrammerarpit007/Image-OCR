from fastapi import APIRouter, UploadFile, File, HTTPException
from datetime import datetime
from app.database import db
from app.schemas.ocr_schema import OCRResponse
from app.services.ocr_service import ocr_service
from app.models.ocr_extraction import create_ocr_table


router = APIRouter(prefix="/api/ocr", tags=["OCR"])

@router.post("/extract", response_model=OCRResponse)
async def extract_ocr(file: UploadFile = File(...)):
    content = await file.read()
    text, confidence = ocr_service.extract_text(content)

    if not text:
        raise HTTPException(400, "No text extracted")

    fields = ocr_service.extract_fields(text)
    doc_type = ocr_service.categorize_document(fields, text)

    conn = db.get_connection()
    cursor = conn.cursor()
    create_ocr_table(cursor)

    cursor.execute("""
        INSERT INTO ocr_extractions
        (filename, document_type, name, email, phone, aadhaar, pan, dob, address, state, country, raw_text, confidence_score)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)

    """, (
        file.filename, doc_type,
        fields["name"], fields["email"], fields["phone"],
        fields["aadhaar"], fields["pan"], fields["dob"],fields["address"],
        fields["state"], fields["country"],
        text, confidence
    ))

    conn.commit()
    extraction_id = cursor.lastrowid
    cursor.close()

    return OCRResponse(
        id=extraction_id,
        filename=file.filename,
        document_type=doc_type,
        extracted_data=fields,
        confidence_score=round(confidence, 4),
        created_at=datetime.now()
    )
