# pip install pandas

from langchain_community.document_loaders import CSVLoader

def load_csv(file_path):
    loader = CSVLoader(file_path)

    documents = loader.load()

    return documents