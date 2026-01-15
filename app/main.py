from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers.ocr import router as ocr_router
from app.database import db
from app.models.ocr_extraction import create_ocr_table
from app.logger import logger

app = FastAPI(title="OCR API")

# -------------------- CORS --------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- ROUTERS --------------------
app.include_router(ocr_router)

# -------------------- STARTUP --------------------
@app.on_event("startup")
def startup_event():
    try:
        logger.info("Starting OCR API...")

        conn = db.get_connection()
        cursor = conn.cursor()

        create_ocr_table(cursor)
        conn.commit()
        cursor.close()

        logger.info("Database table verified/created successfully")

    except Exception as e:
        logger.exception("Startup failed: Unable to initialize database")

# -------------------- ROOT --------------------
@app.get("/")
def root():
    return {"status": "OCR API running"}
