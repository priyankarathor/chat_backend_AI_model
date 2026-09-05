from vectorstore.chroma_store import get_vectorstore
from retriever.retriever import get_retriever


current_retriever = None


def set_retriever(retriever):
    global current_retriever
    current_retriever = retriever


def get_current_retriever():
    return current_retriever


def get_user_retriever(user_id, document_id=None):

    # Get existing ChromaDB
    vectorstore = get_vectorstore()

    # Create retriever for this user, optionally scoped to one document.
    retriever = get_retriever(
        vectorstore,
        user_id,
        document_id
    )

    return retriever
