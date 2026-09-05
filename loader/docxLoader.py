import docx2txt
from langchain_core.documents import Document


def load_docx(file_path):
    text = docx2txt.process(file_path) or ""

    return [
        Document(
            page_content=text,
            metadata={"source": file_path}
        )
    ]
