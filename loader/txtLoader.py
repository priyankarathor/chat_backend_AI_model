from langchain_core.documents import Document

def load_txt(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        text = file.read()

    return [
        Document(
            page_content=text,
            metadata={"source": file_path}
        )
    ]
