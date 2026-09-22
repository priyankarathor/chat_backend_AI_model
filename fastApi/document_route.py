from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Depends
)

from datetime import datetime, timezone

import os
import shutil
import uuid
from pathlib import Path

from pydantic import BaseModel

# ==============================
# Loaders
# ==============================

from loader.pdfLoader import load_pdf
from loader.docxLoader import load_docx
from loader.txtLoader import load_txt
from loader.csvLoader import load_csv
from loader.htmLoader import load_HTML
from loader.imageLoader import load_image
from loader.excelLoader import load_excel
from loader.youtubeurl import load_youtube_url


# ==============================
# Splitter
# ==============================

from splitters.text_splitter import split_document


# ==============================
# Embeddings
# ==============================

from embeddings.embedding import get_embeddings


# ==============================
# Vector Store
# ==============================

from vectorstore.chroma_store import create_vectorstore


# ==============================
# Retriever
# ==============================

from retriever.retriever import get_retriever
from services.rag_services import set_retriever
from rag.chain import ask_question
from llm.groq import GroqConfigError


# ==============================
# Authentication
# ==============================

from utils.security import get_current_user


# ==============================
# MongoDB
# ==============================

from fastApi.mongodb import mongodb


# ==============================
# Router
# ==============================

router = APIRouter()


class YouTubeUrlRequest(BaseModel):
    urls: list[str]
    question: str | None = None
    languages: list[str] | None = None


def has_extractable_text(documents):
    return any(
        document.page_content and document.page_content.strip()
        for document in documents
    )


def get_allowed_extensions_message(file_extension: str) -> str:
    allowed_extensions = ", ".join(
        extension.upper().lstrip(".")
        for extension in ALLOWED_EXTENSIONS
    )

    if not file_extension:
        detected_extension = "no extension"
    else:
        detected_extension = file_extension

    return (
        f"Only {allowed_extensions} files are allowed. "
        f"Detected: {detected_extension}."
    )


def add_user_metadata_to_chunks(
    chunks,
    user_id: str,
    document_id: str,
    filename: str,
    stored_filename: str | None = None
):
    for chunk in chunks:

        if not chunk.metadata:

            chunk.metadata = {}

        metadata = {
            "user_id": user_id,
            "document_id": document_id,
            "filename": filename,
        }

        if stored_filename:
            metadata["stored_filename"] = stored_filename

        chunk.metadata.update(metadata)


# ==============================
# Upload folder
# ==============================

UPLOAD_FOLDER = os.getenv(
    "UPLOAD_FOLDER",
    "/tmp/documents" if os.getenv("VERCEL") else "documents"
)

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)


# ==============================
# Allowed extensions
# ==============================

ALLOWED_EXTENSIONS = [
    ".pdf",
    ".csv",
    ".xlsx",
    ".xls",
    ".html",
    ".htm",
    ".txt",
    ".docx",
    ".png",
    ".jpg",
    ".jpeg",
    ".svg",
    ".webp"
]


# ==========================================================
# UPLOAD YOUTUBE URL
# ==========================================================

@router.post("/youtube-url")
async def upload_youtube_url(

    request: YouTubeUrlRequest,

    current_user: dict = Depends(get_current_user)

):

    user_id = current_user["user_id"]

    if not request.urls:

        raise HTTPException(
            status_code=400,
            detail="At least one YouTube URL is required."
        )

    if mongodb.database is None:

        raise HTTPException(
            status_code=500,
            detail="MongoDB database is not connected."
        )

    documents_collection = mongodb.database[
        "documents"
    ]

    processed_documents = []
    failed_documents = []

    for video_url in request.urls:

        document_id = str(
            uuid.uuid4()
        )

        video_url = video_url.strip()

        if not video_url:

            failed_documents.append({
                "url": video_url,
                "error": "YouTube URL cannot be empty."
            })

            continue

        try:

            await documents_collection.insert_one({

                "document_id": document_id,

                "user_id": user_id,

                "filename": video_url,

                "stored_filename": None,

                "file_path": video_url,

                "file_type": "youtube",

                "status": "processing",

                "documents_count": 0,

                "chunks_count": 0,

                "error_message": None,

                "created_at": datetime.now(
                    timezone.utc
                ),

                "updated_at": datetime.now(
                    timezone.utc
                )

            })

            documents, video_id = load_youtube_url(
                video_url,
                request.languages
            )

            if not documents or not has_extractable_text(documents):

                raise HTTPException(
                    status_code=400,
                    detail="No transcript text could be extracted from this YouTube URL."
                )

            chunks = split_document(
                documents
            )

            if not chunks:

                raise HTTPException(
                    status_code=400,
                    detail="No text chunks were created from this YouTube transcript."
                )

            add_user_metadata_to_chunks(
                chunks,
                user_id,
                document_id,
                video_url
            )

            embedding = get_embeddings()

            vectorstore = create_vectorstore(
                chunks,
                embedding
            )

            retriever = get_retriever(
                vectorstore,
                user_id,
                document_id
            )

            set_retriever(
                retriever
            )

            answer = None

            if request.question:

                answer = ask_question(
                    retriever,
                    request.question
                )

            await documents_collection.update_one(
                {
                    "document_id": document_id
                },
                {
                    "$set": {
                        "status": "completed",
                        "video_id": video_id,
                        "documents_count": len(documents),
                        "chunks_count": len(chunks),
                        "updated_at": datetime.now(
                            timezone.utc
                        )
                    }
                }
            )

            processed_document = {
                "document_id": document_id,
                "url": video_url,
                "video_id": video_id,
                "documents": len(documents),
                "chunks": len(chunks),
                "status": "completed"
            }

            if answer is not None:
                processed_document["question"] = request.question
                processed_document["answer"] = answer

            processed_documents.append(
                processed_document
            )

        except GroqConfigError as e:

            await documents_collection.update_one(
                {
                    "document_id": document_id
                },
                {
                    "$set": {
                        "status": "failed",
                        "error_message": str(e),
                        "updated_at": datetime.now(
                            timezone.utc
                        )
                    }
                }
            )

            raise HTTPException(
                status_code=401,
                detail=str(e)
            )

        except HTTPException as e:

            await documents_collection.update_one(
                {
                    "document_id": document_id
                },
                {
                    "$set": {
                        "status": "failed",
                        "error_message": str(e.detail),
                        "updated_at": datetime.now(
                            timezone.utc
                        )
                    }
                }
            )

            failed_documents.append({
                "document_id": document_id,
                "url": video_url,
                "error": str(e.detail)
            })

        except Exception as e:

            await documents_collection.update_one(
                {
                    "document_id": document_id
                },
                {
                    "$set": {
                        "status": "failed",
                        "error_message": str(e),
                        "updated_at": datetime.now(
                            timezone.utc
                        )
                    }
                }
            )

            failed_documents.append({
                "document_id": document_id,
                "url": video_url,
                "error": str(e)
            })

    if not processed_documents:

        raise HTTPException(
            status_code=400,
            detail={
                "message": "No YouTube URLs were processed successfully.",
                "failed": failed_documents
            }
        )

    return {
        "success": True,
        "message": "YouTube URL transcripts processed successfully.",
        "user_id": user_id,
        "documents": processed_documents,
        "failed": failed_documents
    }


# ==========================================================
# UPLOAD DOCUMENT
# ==========================================================

@router.post("/upload-document")
async def upload_document(

    # Uploaded file
    file: UploadFile = File(...),

    # JWT authentication
    current_user: dict = Depends(get_current_user)

):

    # ======================================================
    # STEP 1: GET USER ID FROM JWT
    # ======================================================

    user_id = current_user["user_id"]

    print(
        "Logged in user:",
        user_id
    )


    # ======================================================
    # STEP 2: VALIDATE FILE NAME
    # ======================================================

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="Filename is required."
        )

    original_filename = Path(
        file.filename.strip()
    ).name

    if not original_filename:

        raise HTTPException(
            status_code=400,
            detail="Filename is required."
        )


    # ======================================================
    # STEP 3: GET FILE EXTENSION
    # ======================================================

    file_extension = os.path.splitext(
        original_filename
    )[1].lower()


    # ======================================================
    # STEP 4: VALIDATE FILE EXTENSION
    # ======================================================

    if file_extension not in ALLOWED_EXTENSIONS:

        raise HTTPException(
            status_code=400,
            detail=get_allowed_extensions_message(file_extension)
        )


    # ======================================================
    # STEP 5: CREATE USER FOLDER
    # ======================================================

    user_folder = os.path.join(
        UPLOAD_FOLDER,
        user_id
    )

    os.makedirs(
        user_folder,
        exist_ok=True
    )


    # ======================================================
    # STEP 6: CREATE UNIQUE FILE NAME
    # ======================================================

    unique_filename = (
        f"{uuid.uuid4().hex}_"
        f"{original_filename}"
    )


    # ======================================================
    # STEP 7: CREATE FILE PATH
    # ======================================================

    file_path = os.path.join(
        user_folder,
        unique_filename
    )

    document_id = str(
        uuid.uuid4()
    )


    print(
        "File path:",
        file_path
    )

    documents_collection = None


    try:

        # ==================================================
        # STEP 8: SAVE FILE
        # ==================================================

        with open(
            file_path,
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer
            )


        print(
            "File saved successfully:",
            file_path
        )

        if mongodb.database is None:

            raise HTTPException(
                status_code=500,
                detail="MongoDB database is not connected."
            )

        documents_collection = mongodb.database[
            "documents"
        ]

        await documents_collection.insert_one({

            "document_id": document_id,

            "user_id": user_id,

            "filename": original_filename,

            "stored_filename": unique_filename,

            "file_path": file_path,

            "file_type": file_extension,

            "status": "processing",

            "documents_count": 0,

            "chunks_count": 0,

            "error_message": None,

            "created_at": datetime.now(
                timezone.utc
            ),

            "updated_at": datetime.now(
                timezone.utc
            )

        })


        print(
            "Document metadata saved in MongoDB with processing status"
        )


        # ==================================================
        # STEP 9: LOAD DOCUMENT
        # ==================================================

        if file_extension == ".pdf":

            documents = load_pdf(
                file_path
            )


        elif file_extension == ".docx":

            documents = load_docx(
                file_path
            )


        elif file_extension == ".txt":

            documents = load_txt(
                file_path
            )


        elif file_extension == ".csv":

            documents = load_csv(
                file_path
            )


        elif file_extension in [
            ".html",
            ".htm"
        ]:

            documents = load_HTML(
                file_path
            )


        elif file_extension in [
            ".png",
            ".jpg",
            ".jpeg",
            ".svg",
            ".webp"
        ]:

            documents = load_image(
                file_path
            )


        elif file_extension in [
            ".xlsx",
            ".xls"
        ]:
            documents = load_excel(
                file_path
            )


        else:

            raise HTTPException(
                status_code=400,
                detail="Unsupported file type."
            )


        print(
            "Documents loaded:",
            len(documents)
        )

        if not documents or not has_extractable_text(documents):

            raise HTTPException(
                status_code=400,
                detail=(
                    "No readable text could be extracted from this file. "
                    "The file may be scanned, image-only, corrupted, or encrypted."
                )
            )


        # ==================================================
        # STEP 10: SPLIT DOCUMENT
        # ==================================================

        chunks = split_document(
            documents
        )


        print(
            "Chunks created:",
            len(chunks)
        )

        if not chunks:

            raise HTTPException(
                status_code=400,
                detail=(
                    "No text chunks were created from this file. "
                    "Please upload a document with extractable text."
                )
            )


        # ==================================================
        # STEP 12: ADD USER METADATA TO CHUNKS
        # ==================================================

        add_user_metadata_to_chunks(
            chunks,
            user_id,
            document_id,
            original_filename,
            unique_filename
        )


        print(
            "User metadata added to chunks"
        )


        # ==================================================
        # STEP 13: LOAD EMBEDDING MODEL
        # ==================================================

        embedding = get_embeddings()


        print(
            "Embedding model loaded"
        )


        # ==================================================
        # STEP 14: CREATE CHROMA VECTOR STORE
        # ==================================================

        vectorstore = create_vectorstore(
            chunks,
            embedding
        )


        print(
            "Vector store created"
        )


        # ==================================================
        # STEP 15: CREATE RETRIEVER
        # ==================================================

        retriever = get_retriever(
                vectorstore,
                user_id,
                document_id
            )

        # ==================================================
        # STEP 16: SAVE RETRIEVER
        # ==================================================

        set_retriever(
            retriever
        )


        print(
            "Retriever saved"
        )


        # ==================================================
        # STEP 17: SAVE DOCUMENT METADATA IN MONGODB
        # ==================================================

        await documents_collection.update_one(
            {
                "document_id": document_id
            },
            {
                "$set": {
                    "status": "completed",
                    "documents_count": len(documents),
                    "chunks_count": len(chunks),
                    "updated_at": datetime.now(
                        timezone.utc
                    )
                }
            }
        )


        print(
            "Document metadata updated in MongoDB with completed status"
        )


        # ==================================================
        # STEP 18: SUCCESS RESPONSE
        # ==================================================

        return {

            "success": True,

            "message": (
                "Document uploaded and "
                "processed successfully."
            ),

            "user_id": user_id,

            "document_id": document_id,

            "filename": original_filename,

            "file_type": file_extension,

            "documents": len(documents),

            "chunks": len(chunks)

        }


    # ======================================================
    # HTTP EXCEPTION
    # ======================================================

    except HTTPException as e:

        if documents_collection is not None:

            await documents_collection.update_one(
                {
                    "document_id": document_id
                },
                {
                    "$set": {
                        "status": "failed",
                        "error_message": str(e.detail),
                        "updated_at": datetime.now(
                            timezone.utc
                        )
                    }
                }
            )

        raise


    # ======================================================
    # GENERAL ERROR
    # ======================================================

    except Exception as e:

        print(
            "Error processing document:",
            str(e)
        )

        if documents_collection is not None:

            await documents_collection.update_one(
                {
                    "document_id": document_id
                },
                {
                    "$set": {
                        "status": "failed",
                        "error_message": str(e),
                        "updated_at": datetime.now(
                            timezone.utc
                        )
                    }
                }
            )


        # ==============================================
        # Delete uploaded file if processing fails
        # ==============================================

        if os.path.exists(file_path):

            try:

                os.remove(file_path)

            except Exception:

                pass


        raise HTTPException(

            status_code=500,

            detail=(
                f"Error processing document: {str(e)}"
            )

        )
