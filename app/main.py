from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers.ocr import router as ocr_router

app = FastAPI(title="OCR API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ocr_router)

@app.get("/")
def root():
    return {"status": "OCR API running"}
