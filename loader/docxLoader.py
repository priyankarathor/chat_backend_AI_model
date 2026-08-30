# pip install docx2txt
from langchain_community.document_loaders import Docx2txtLoader


def load_docx(file_path):

    loader = Docx2txtLoader(file_path)

    documents = loader.load()

    return documents