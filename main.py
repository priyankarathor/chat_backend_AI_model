from contextlib import asynccontextmanager

from fastapi import FastAPI

from fastApi.document_route import router as document_router
from fastApi.chat_route import router as chat_router
from fastApi.mongodb import (
    connect_to_mongodb,
    close_mongodb_connection,
)

from app.api.vi.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):

    # =========================
    # STARTUP
    # =========================
    try:
        await connect_to_mongodb()
        print("✅ MongoDB startup connection successful")

    except Exception as e:
        print(f"⚠️ MongoDB startup connection failed: {e}")
        print("⚠️ FastAPI will continue starting...")

    yield

    # =========================
    # SHUTDOWN
    # =========================
    try:
        await close_mongodb_connection()
        print("✅ MongoDB connection closed")

    except Exception as e:
        print(f"⚠️ MongoDB shutdown error: {e}")


app = FastAPI(
    title="Documents AI Chatboard",
    description="Upload documents and chat with them",
    version="1.0.0",
    lifespan=lifespan,
)


# =========================
# ROOT
# =========================

@app.get("/")
async def home():
    return {
        "status": "success",
        "message": "Welcome to Documents AI Chatboard"
    }


# =========================
# HEALTH CHECK
# =========================

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "message": "FastAPI server is running"
    }


# =========================
# DOCUMENT ROUTES
# =========================

app.include_router(
    document_router,
    prefix="/documents",
    tags=["Documents"]
)


# =========================
# CHAT ROUTES
# =========================

app.include_router(
    chat_router,
    prefix="/chat",
    tags=["Chat"]
)


# =========================
# AUTH ROUTES
# =========================

app.include_router(
    auth_router
)
