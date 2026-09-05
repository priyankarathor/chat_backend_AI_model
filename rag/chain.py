from llm.groq import get_groq_response


def ask_question(retriever, question):
    if hasattr(retriever, "invoke"):
        documents = retriever.invoke(question)
    else:
        documents = retriever.get_relevant_documents(question)

    context = "\n\n".join(
        f"Source {index}:\n{document.page_content}"
        for index, document in enumerate(documents, start=1)
    )

    if not context.strip():
        return "I could not find relevant content in the uploaded document."

    prompt = f"""
Answer the question using only the document context below.
Do not use outside knowledge.
If the document context does not contain the answer, reply exactly:
I could not find that in the uploaded document.

Document context:
{context}

Question:
{question}
"""

    return get_groq_response(prompt)
