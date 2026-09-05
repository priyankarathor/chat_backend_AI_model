import os

from langchain_chroma import Chroma

from embeddings.embedding import get_embeddings


COLLECTION_NAME = "documents"

PERSIST_DIRECTORY = os.getenv(
    "CHROMA_PERSIST_DIRECTORY",
    "/tmp/chroma_db" if os.getenv("VERCEL") else "./chroma_db"
)


def get_vectorstore():

    embeddings = get_embeddings()

    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=PERSIST_DIRECTORY
    )

    return vectorstore


def create_vectorstore(chunks, embeddings):

    if not chunks:
        raise ValueError("Cannot create vectorstore without document chunks.")

    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=PERSIST_DIRECTORY
    )

    vectorstore.add_documents(
        documents=chunks
    )

    return vectorstore
