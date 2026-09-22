def get_retriever(vectorstore, user_id, document_id=None):

    metadata_filter = {
        "user_id": user_id
    }

    if document_id:
        metadata_filter["document_id"] = document_id

    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": 8,

            # Only retrieve chunks belonging to the selected scope.
            "filter": metadata_filter
        }
    )

    return retriever
