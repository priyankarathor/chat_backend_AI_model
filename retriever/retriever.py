def get_retriever(vectorstore, user_id):

    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": 5,
            "fetch_k": 20,

            # Only retrieve documents belonging
            # to the logged-in user
            "filter": {
                "user_id": user_id
            }
        }
    )

    return retriever