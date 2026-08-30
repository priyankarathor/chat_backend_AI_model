from langchain_community.document_loaders import TextLoader

def load_txt(file_path):
    loader = TextLoader(
        file_path,
        encoding="utf-8"
    )

    documents = loader.load()

    return documents