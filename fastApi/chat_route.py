from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from services.rag_services import get_user_retriever
from utils.security import get_current_user
from rag.chain import ask_question
from llm.groq import GroqConfigError


router = APIRouter()


class QuestionRequest(BaseModel):
    question: str


@router.post("/ask")
def ask_document(
    request: QuestionRequest,
    current_user: dict = Depends(get_current_user)
):

    user_id = current_user["user_id"]

    retriever = get_user_retriever(user_id)

    # Check if a document has been uploaded
    if retriever is None:
        raise HTTPException(
            status_code=400,
            detail="Please upload a document first."
        )

    try:
        answer = ask_question(
            retriever,
            request.question
        )
    except GroqConfigError as e:
        raise HTTPException(
            status_code=401,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error answering question: {str(e)}"
        )

    return {
        "user_id": user_id,
        "question": request.question,
        "answer": answer
    }
