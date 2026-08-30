# pip install langchain-huggingface sentence-transformers
# sentence-transformers/all-MiniLM-L6-v2

from langchain_huggingface import HuggingFaceEmbeddings


def get_embeddings():
    embeddings = HuggingFaceEmbeddings(
        model_name = "sentence-transformers/all-MiniLM-L6-v2"
    )

    return embeddings


get_enbeddings = get_embeddings
