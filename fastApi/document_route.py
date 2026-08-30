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

# ==============================
# Loaders
# ==============================

from loader.pdfLoader import load_pdf
from loader.docxLoader import load_docx
from loader.txtLoader import load_txt
from loader.csvLoader import load_csv
from loader.htmLoader import load_HTML
from loader.imageLoader import load_image


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


def has_extractable_text(documents):
    return any(
        document.page_content and document.page_content.strip()
        for document in documents
    )


# ==============================
# Upload folder
# ==============================

UPLOAD_FOLDER = "documents"

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


    # ======================================================
    # STEP 3: GET FILE EXTENSION
    # ======================================================

    file_extension = os.path.splitext(
        file.filename
    )[1].lower()


    # ======================================================
    # STEP 4: VALIDATE FILE EXTENSION
    # ======================================================

    if file_extension not in ALLOWED_EXTENSIONS:

        raise HTTPException(
            status_code=400,
            detail=(
                "Only PDF, CSV, Excel, HTML, TXT, DOCX, "
                "PNG, JPG, JPEG, SVG and WEBP files are allowed."
            )
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
        f"{file.filename}"
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

            "filename": file.filename,

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

            raise HTTPException(
                status_code=400,
                detail="Excel loader is not implemented yet."
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

        for chunk in chunks:

            if not chunk.metadata:

                chunk.metadata = {}


            chunk.metadata.update({

                "user_id": user_id,

                "document_id": document_id,

                "filename": file.filename,

                "stored_filename": unique_filename

            })


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
                user_id
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

            "filename": file.filename,

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
