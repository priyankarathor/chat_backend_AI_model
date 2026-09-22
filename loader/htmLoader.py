from bs4 import BeautifulSoup
from langchain_core.documents import Document

def load_HTML(file_path):
    with open(file_path, "rb") as file:
        soup = BeautifulSoup(file.read(), "html.parser")

    for element in soup(["script", "style", "noscript"]):
        element.decompose()

    return [
        Document(
            page_content=soup.get_text(separator="\n", strip=True),
            metadata={"source": file_path}
        )
    ]
