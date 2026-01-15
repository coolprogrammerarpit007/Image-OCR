from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import mysql.connector
from mysql.connector import Error
import re
import io
from PIL import Image
import tempfile

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MySQLConnection:
    def __init__(self):
        self.host = os.environ.get('MYSQL_HOST')
        self.user = os.environ.get('MYSQL_USER')
        self.password = os.environ.get('MYSQL_PASSWORD')
        self.database = os.environ.get('MYSQL_DATABASE')
        self.connection = None
        self.init_database()
    
    def get_connection(self):
        try:
            if self.connection is None or not self.connection.is_connected():
                self.connection = mysql.connector.connect(
                    host=self.host,
                    user=self.user,
                    password=self.password,
                    database=self.database
                )
            return self.connection
        except Error as e:
            logger.error(f"MySQL connection error: {e}")
            raise HTTPException(status_code=500, detail="Database connection failed")
    
    def init_database(self):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            create_table_query = """
            CREATE TABLE IF NOT EXISTS ocr_extractions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
                document_type VARCHAR(50) NOT NULL,
                name VARCHAR(255),
                email VARCHAR(255),
                phone VARCHAR(50),
                aadhaar VARCHAR(20),
                pan VARCHAR(20),
                address TEXT,
                raw_text TEXT,
                confidence_score FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_document_type (document_type),
                INDEX idx_created_at (created_at)
            )
            """
            cursor.execute(create_table_query)
            conn.commit()
            cursor.close()
            logger.info("Database initialized successfully")
        except Error as e:
            logger.error(f"Database initialization error: {e}")

db = MySQLConnection()

class OCRExtractor:
    def __init__(self):
        from paddleocr import PaddleOCR
        self.ocr = PaddleOCR(use_angle_cls=True, lang='en')
    
    def extract_text_from_image(self, image_bytes: bytes) -> tuple:
        try:
            image = Image.open(io.BytesIO(image_bytes))
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                image.save(tmp_file.name)
                tmp_path = tmp_file.name
            
            result = self.ocr.ocr(tmp_path)
            
            os.unlink(tmp_path)
            
            if result and result[0]:
                text_lines = [line[1][0] for line in result[0]]
                full_text = ' '.join(text_lines)
                avg_confidence = sum([line[1][1] for line in result[0]]) / len(result[0])
                return full_text, avg_confidence
            else:
                return "", 0.0
        except Exception as e:
            logger.error(f"OCR extraction error: {e}")
            return "", 0.0
    
    def extract_fields(self, text: str) -> Dict[str, Optional[str]]:
        fields = {
            'name': None,
            'email': None,
            'phone': None,
            'aadhaar': None,
            'pan': None,
            'address': None
        }
        
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            fields['email'] = emails[0]
        
        phone_patterns = [
            r'\+?\d{1,3}[-\s]?\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}',
            r'\b\d{10}\b',
            r'\b\d{3}[-\s]\d{3}[-\s]\d{4}\b'
        ]
        for pattern in phone_patterns:
            phones = re.findall(pattern, text)
            if phones:
                fields['phone'] = phones[0]
                break
        
        aadhaar_pattern = r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
        aadhaars = re.findall(aadhaar_pattern, text)
        if aadhaars:
            fields['aadhaar'] = aadhaars[0].replace('-', '').replace(' ', '')
        
        pan_pattern = r'\b[A-Z]{5}\d{4}[A-Z]\b'
        pans = re.findall(pan_pattern, text)
        if pans:
            fields['pan'] = pans[0]
        
        name_keywords = ['name', 'Name', 'NAME']
        lines = text.split('\n')
        for i, line in enumerate(lines):
            for keyword in name_keywords:
                if keyword in line:
                    name_match = re.search(rf'{keyword}[:\s]+([A-Za-z\s]+)', line)
                    if name_match:
                        fields['name'] = name_match.group(1).strip()
                        break
            if fields['name']:
                break
        
        if not fields['name']:
            words = text.split()
            for i, word in enumerate(words):
                if word.lower() in ['name', 'name:']:
                    if i + 1 < len(words):
                        potential_name = ' '.join(words[i+1:i+4])
                        if re.match(r'^[A-Z][a-z]+(\s[A-Z][a-z]+)*$', potential_name.strip()):
                            fields['name'] = potential_name.strip()
                            break
        
        address_keywords = ['address', 'Address', 'ADDRESS']
        for i, line in enumerate(lines):
            for keyword in address_keywords:
                if keyword in line:
                    address_lines = []
                    start_idx = i
                    for j in range(start_idx, min(start_idx + 3, len(lines))):
                        address_lines.append(lines[j])
                    fields['address'] = ' '.join(address_lines).strip()
                    break
            if fields['address']:
                break
        
        return fields
    
    def categorize_document(self, fields: Dict[str, Optional[str]]) -> str:
        if fields.get('aadhaar') or fields.get('pan'):
            return 'ID_CARD'
        elif fields.get('email') and fields.get('phone') and fields.get('name'):
            if fields.get('address'):
                return 'BUSINESS_CARD'
            return 'GENERAL_DOCUMENT'
        else:
            return 'GENERAL_DOCUMENT'

ocr_extractor = OCRExtractor()

class ExtractionResponse(BaseModel):
    id: int
    filename: str
    document_type: str
    extracted_data: Dict[str, Any]
    confidence_score: float
    created_at: datetime

@api_router.post("/ocr/extract", response_model=ExtractionResponse)
async def extract_text(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        
        full_text, confidence = ocr_extractor.extract_text_from_image(contents)
        
        if not full_text:
            raise HTTPException(status_code=400, detail="No text could be extracted from the image")
        
        fields = ocr_extractor.extract_fields(full_text)
        document_type = ocr_extractor.categorize_document(fields)
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        insert_query = """
        INSERT INTO ocr_extractions 
        (filename, document_type, name, email, phone, aadhaar, pan, address, raw_text, confidence_score)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(insert_query, (
            file.filename,
            document_type,
            fields.get('name'),
            fields.get('email'),
            fields.get('phone'),
            fields.get('aadhaar'),
            fields.get('pan'),
            fields.get('address'),
            full_text,
            confidence
        ))
        
        conn.commit()
        extraction_id = cursor.lastrowid
        cursor.close()
        
        return ExtractionResponse(
            id=extraction_id,
            filename=file.filename,
            document_type=document_type,
            extracted_data=fields,
            confidence_score=round(confidence, 4),
            created_at=datetime.now()
        )
    
    except Exception as e:
        logger.error(f"Extraction error: {e}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

@api_router.get("/ocr/history", response_model=List[ExtractionResponse])
async def get_extraction_history():
    try:
        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT id, filename, document_type, name, email, phone, aadhaar, pan, 
               address, confidence_score, created_at
        FROM ocr_extractions
        ORDER BY created_at DESC
        LIMIT 100
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        
        response = []
        for row in results:
            extracted_data = {
                'name': row['name'],
                'email': row['email'],
                'phone': row['phone'],
                'aadhaar': row['aadhaar'],
                'pan': row['pan'],
                'address': row['address']
            }
            response.append(ExtractionResponse(
                id=row['id'],
                filename=row['filename'],
                document_type=row['document_type'],
                extracted_data=extracted_data,
                confidence_score=round(row['confidence_score'], 4),
                created_at=row['created_at']
            ))
        
        return response
    
    except Exception as e:
        logger.error(f"History retrieval error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve history: {str(e)}")

@api_router.get("/ocr/extract/{extraction_id}", response_model=ExtractionResponse)
async def get_extraction_by_id(extraction_id: int):
    try:
        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT id, filename, document_type, name, email, phone, aadhaar, pan, 
               address, confidence_score, created_at
        FROM ocr_extractions
        WHERE id = %s
        """
        
        cursor.execute(query, (extraction_id,))
        row = cursor.fetchone()
        cursor.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Extraction not found")
        
        extracted_data = {
            'name': row['name'],
            'email': row['email'],
            'phone': row['phone'],
            'aadhaar': row['aadhaar'],
            'pan': row['pan'],
            'address': row['address']
        }
        
        return ExtractionResponse(
            id=row['id'],
            filename=row['filename'],
            document_type=row['document_type'],
            extracted_data=extracted_data,
            confidence_score=round(row['confidence_score'], 4),
            created_at=row['created_at']
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Retrieval error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve extraction: {str(e)}")

@api_router.get("/")
async def root():
    return {"message": "OCR API is running", "status": "active"}

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_event():
    if db.connection and db.connection.is_connected():
        db.connection.close()
        logger.info("MySQL connection closed")