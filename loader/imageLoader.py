# pip install pytesseract pillow

from PIL import Image
import pytesseract
from langchain_core.documents import Document

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

def load_image(file_path):

    image = Image.open(file_path)

    text = pytesseract.image_to_string(image)

    return [
        Document(
            page_content=text,
            metadata={"source": file_path}
        )
    ]
