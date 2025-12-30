from app.agents.base import BaseAgent
from typing import Dict, Any, Tuple
import pypdf
import os
from PIL import Image
import pytesseract


class IngestionAgent(BaseAgent):
    """
    Agent responsible for text extraction from documents.
    Supports PDF parsing and image OCR.
    """
    
    SUPPORTED_PDF_EXTENSIONS = ['.pdf']
    SUPPORTED_IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif', '.webp']
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        file_path = input_data.get('file_path')
        if not file_path or not os.path.exists(file_path):
            raise ValueError("Invalid file path provided")

        file_ext = os.path.splitext(file_path)[1].lower()
        filename = os.path.basename(file_path)
        
        if file_ext in self.SUPPORTED_PDF_EXTENSIONS:
            text, num_pages = self._extract_from_pdf(file_path)
            file_type = "pdf"
        elif file_ext in self.SUPPORTED_IMAGE_EXTENSIONS:
            text = self._extract_from_image(file_path)
            num_pages = 1
            file_type = "image"
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
        
        return {
            "text": text,
            "metadata": {
                "source": filename,
                "file_type": file_type,
                "pages": num_pages
            },
            "file_type": file_type,
            "pages": num_pages
        }

    def _extract_from_pdf(self, file_path: str) -> Tuple[str, int]:
        with open(file_path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            text = ""
            num_pages = len(reader.pages)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text, num_pages
    
    def _extract_from_image(self, file_path: str) -> str:
        try:
            image = Image.open(file_path)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            raise ValueError(f"OCR extraction failed: {str(e)}")
