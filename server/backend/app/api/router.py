from fastapi import APIRouter

from app.api.v1.ocr import router as ocr
from app.api.v1.user import router as users

api_router = APIRouter()
api_router.include_router(ocr, prefix="/v1")
api_router.include_router(users, prefix="/v1")
