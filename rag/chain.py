from llm.groq import get_groq_response


def ask_question(retriever, question):
    question = question.strip()

    if not question:
        raise ValueError("Question cannot be empty.")

    if hasattr(retriever, "invoke"):
        documents = retriever.invoke(question)
    else:
        documents = retriever.get_relevant_documents(question)

    context = "\n\n".join(
        (
            f"Source {index} "
            f"({document.metadata.get('filename', 'document')}, "
            f"page/row {document.metadata.get('page', document.metadata.get('row', 'n/a'))}):\n"
            f"{document.page_content}"
        )
        for index, document in enumerate(documents, start=1)
    )

    if not context.strip():
        return "I could not find relevant content in the uploaded document."

    prompt = f"""
Answer the question using only the document context below.
Do not use outside knowledge.
Answer in the same language as the question unless the user explicitly asks for another language.
Combine relevant details from all supplied sources and be precise.
If the context does not contain the answer, clearly say so in the same language as the question.

Document context:
{context}

Question:
{question}
"""

    return get_groq_response(prompt)
