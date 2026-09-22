from langchain_core.documents import Document
from loader.text_utils import read_text_file

def load_txt(file_path):
    text = read_text_file(file_path)

    return [
        Document(
            page_content=text,
            metadata={"source": file_path}
        )
    ]
