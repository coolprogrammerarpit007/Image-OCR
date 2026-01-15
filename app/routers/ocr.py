from fastapi import APIRouter, UploadFile, File, HTTPException
from datetime import datetime

from app.database import db
from app.services.ocr_service import ocr_service
from app.models.ocr_extraction import create_ocr_table
from app.utils.response import success_response, error_response
from app.logger import logger

router = APIRouter(prefix="/api/ocr", tags=["OCR"])


@router.post("/extract")
async def extract_ocr(file: UploadFile = File(...)):
    try:
        if not file.content_type.startswith("image/"):
            return error_response("Only image files are allowed")

        image_bytes = await file.read()

        # ---------- OCR ----------
        text, confidence = ocr_service.extract_text(image_bytes)

        if not text.strip():
            return error_response("No readable text found in image")

        # ---------- FIELD EXTRACTION ----------
        fields = ocr_service.extract_fields(text)
        document_type = ocr_service.categorize_document(fields, text)

        # ---------- SAVE TO DB ----------
        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO ocr_extractions
            (filename, document_type, name, email, phone, aadhaar, pan, dob,
             address, state, country, raw_text, confidence_score)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            file.filename,
            document_type,
            fields.get("name"),
            fields.get("email"),
            fields.get("phone"),
            fields.get("aadhaar"),
            fields.get("pan"),
            fields.get("dob"),
            fields.get("address"),
            fields.get("state"),
            fields.get("country"),
            text,
            confidence
        ))

        conn.commit()
        extraction_id = cursor.lastrowid
        cursor.close()

        return success_response(
            message="OCR extraction successful",
            data={
                "id": extraction_id,
                "document_type": document_type,
                "extracted_data": fields,
                "confidence_score": round(confidence, 4)
            }
        )

    except Exception as e:
        logger.exception("OCR extraction failed")
        return error_response(
            message="OCR extraction failed",
            error=str(e)
        )
