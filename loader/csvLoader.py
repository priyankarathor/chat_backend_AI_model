import csv
import io

from langchain_core.documents import Document
from loader.text_utils import read_text_file

def load_csv(file_path):
    documents = []
    text = read_text_file(file_path)

    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(text, newline=""), dialect=dialect)

    for index, row in enumerate(reader, start=1):
        page_content = "\n".join(
            f"{key or 'column'}: {value or ''}"
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
