from fastapi import APIRouter, UploadFile, File
from fastapi.concurrency import run_in_threadpool
from app.services.ocr_pipeline import run_ocr_single

router = APIRouter(tags=["Ocr"])


@router.post("/ocr")
async def ocr_image(file: UploadFile = File(...)):
    data = await file.read()

    boxes, frames, md5 = await run_in_threadpool(
        run_ocr_single,
        data
    )

    return {
        "md5": md5,
        "boxes": [b.dict() for b in boxes],
        "frames": [f.dict() for f in frames],
    }