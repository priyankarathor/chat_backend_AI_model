def get_retriever(vectorstore, user_id, document_id=None):

    metadata_filter = {
        "user_id": user_id
    }

    if document_id:
        metadata_filter["document_id"] = document_id

    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": 5,
            "fetch_k": 20,

            # Only retrieve chunks belonging to the selected scope.
            "filter": metadata_filter
        }
    )

    return retriever
