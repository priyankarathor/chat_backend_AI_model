from langchain_community.document_loaders import BSHTMLLoader

def load_HTML(file_path):
    loader = BSHTMLLoader(file_path)

    documents = loader.load()

    return documents