from pydantic import BaseModel


class ocr_get(BaseModel):
    status: str
    service: str


class MangaTextBox(BaseModel):
    x: int
    y: int
    w: int
    h: int
    text: str = ""