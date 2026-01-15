from contextlib import asynccontextmanager
from app.services.models import load_models
from app.core.state import app_state


@asynccontextmanager
async def lifespan(app):
    app_state.mocr, app_state.yolo = load_models()
    yield
