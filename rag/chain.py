from llm.groq import get_groq_response


def ask_question(retriever, question):
    if hasattr(retriever, "invoke"):
        documents = retriever.invoke(question)
    else:
        documents = retriever.get_relevant_documents(question)

    context = "\n\n".join(document.page_content for document in documents)

    if not context.strip():
        return "I could not find relevant content in the uploaded document."

    prompt = f"""
Use the document context below to answer the question.

Context:
{context}

Question:
{question}
"""

    return get_groq_response(prompt)
