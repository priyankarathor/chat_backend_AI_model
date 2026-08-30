from contextlib import asynccontextmanager
from fastapi import FastAPI

from fastApi.document_route import router as document_router
from fastApi.chat_route import router as chat_router
from fastApi.mongodb import connect_to_mongodb, close_mongodb_connection

from app.api.vi.auth import router as auth_router
import pytesseract
@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongodb()
    yield
    await close_mongodb_connection()


app = FastAPI(
    title="Documents AI Chatboard",
    description="Upload documents and chat with them",
    lifespan=lifespan
)


@app.get("/")
def home():
    return {
        "message": "Welcome to Documents AI Chatboard"
    }


app.include_router(
    document_router,
    prefix="/documents",
    tags=["Documents"]
)


app.include_router(
    chat_router,
    prefix="/chat",
    tags=["Chat"]
)


app.include_router(auth_router)