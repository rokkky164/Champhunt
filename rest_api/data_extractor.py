import PyPDF2
import pytesseract

from pdf2image import convert_from_path
from PIL import Image


class DataExtractor(object):
    def extract_text_from_pdf(filepath):
        pdfFileObj = open(filepath, "rb")
        pdfReader = PyPDF2.PdfFileReader(pdfFileObj)
        no_of_pages = print(pdfReader.numPages)
        pageObj = pdfReader.getPage(0)
        text = print(pageObj.extractText())
        pdfFileObj.close()
        return text, no_of_pages

    def extract_text_from_image(filepath):
        pages = convert_from_path(filepath, 500)
        for page in pages:
            page.save("out.jpg", "JPEG")
        extracted_text = pytesseract.image_to_string(Image.open("out.jpg"), lang="eng")
        return extracted_text
