from fastapi import APIRouter

from app.api.v1.ocr import router as ocr

api_router = APIRouter()
api_router.include_router(ocr, prefix="/v1")
