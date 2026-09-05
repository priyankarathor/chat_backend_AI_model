from bs4 import BeautifulSoup
from langchain_core.documents import Document

def load_HTML(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "html.parser")

    return [
        Document(
            page_content=soup.get_text(separator="\n"),
            metadata={"source": file_path}
        )
    ]
