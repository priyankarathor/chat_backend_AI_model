# pip install pytesseract pillow

import os

from PIL import Image
import pytesseract
from langchain_core.documents import Document

tesseract_cmd = os.getenv("TESSERACT_CMD")

if tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

def load_image(file_path):

    image = Image.open(file_path)

    text = pytesseract.image_to_string(image)

    return [
        Document(
            page_content=text,
            metadata={"source": file_path}
        )
    ]
