import time
from fastapi import FastAPI, Request

from app.core.config import settings
from app.core.lifespan import lifespan
from app.api.router import api_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.app_debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vue dev-сервер
        "http://127.0.0.1:5173", 
        "http://192.168.0.49:5173",   
        "http://*"
    ],
    allow_credentials=True,
    allow_methods=["*"],           # Разрешаем все методы (GET, POST и т.д.)
    allow_headers=["*"],           # Разрешаем все заголовки
)
@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = (time.perf_counter() - start) * 1000

    response.headers["X-Process-Time"] = f"{elapsed:.2f}ms"
    return response

app.include_router(api_router)
