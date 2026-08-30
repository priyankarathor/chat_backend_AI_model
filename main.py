from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastApi.document_route import router as document_router
from fastApi.chat_route import router as chat_router
from fastApi.mongodb import (
    connect_to_mongodb,
    close_mongodb_connection,
)

from app.api.vi.auth import router as auth_router


# ---------------------------------------------------------
# Application Lifespan
# ---------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs when the FastAPI application starts and stops.
    """

    # Connect to MongoDB when application starts
    await connect_to_mongodb()

    yield

    # Close MongoDB connection when application stops
    await close_mongodb_connection()


# ---------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------
app = FastAPI(
    title="Documents AI Chatboard",
    description="Upload documents and chat with them",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------
# CORS Configuration
# ---------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Root Route
# ---------------------------------------------------------
@app.get("/")
async def home():
    return {
        "message": "Welcome to Documents AI Chatboard",
        "status": "running",
    }


# ---------------------------------------------------------
# Health Check Route
# ---------------------------------------------------------
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
    }


# ---------------------------------------------------------
# Document Routes
# ---------------------------------------------------------
app.include_router(
    document_router,
    prefix="/documents",
    tags=["Documents"],
)


# ---------------------------------------------------------
# Chat Routes
# ---------------------------------------------------------
app.include_router(
    chat_router,
    prefix="/chat",
    tags=["Chat"],
)


# ---------------------------------------------------------
# Authentication Routes
# ---------------------------------------------------------
app.include_router(auth_router)