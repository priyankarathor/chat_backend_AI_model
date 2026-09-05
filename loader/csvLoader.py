import csv

from langchain_core.documents import Document

def load_csv(file_path):
    documents = []

    with open(file_path, "r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        for index, row in enumerate(reader):
            page_content = "\n".join(
                f"{key}: {value}"
                for key, value in row.items()
            )
            documents.append(
                Document(
                    page_content=page_content,
                    metadata={
                        "source": file_path,
                        "row": index
                    }
                )
            )

    return documents
