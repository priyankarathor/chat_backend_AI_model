from langchain_core.documents import Document
from pypdf import PdfReader


def load_pdf(file_path):
    reader = PdfReader(file_path)

    documents = []

    for index, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        documents.append(
            Document(
                page_content=text,
                metadata={
                    "source": file_path,
                    "page": index
                }
            )
        )

    return documents
