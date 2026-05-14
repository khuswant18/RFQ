"""OCR Agent - Converts images/PDFs to clean, structured raw text."""
import base64
import logging
from typing import Optional
from pathlib import Path

from app.core.groq_client import GroqClient
from app.models.rfq import OCRInput, OCROutput

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

logger = logging.getLogger("srip.ocr")


class OCRAgent:
    """
    OCR Agent: Converts image/PDF to clean, structured raw text.
    Strategy:
      1. For PDFs → try pdfplumber text extraction first (fast, accurate for typed PDFs)
      2. If pdfplumber gets <100 chars → treat as scanned, convert to image and use vision
      3. For images → preprocess + Groq Vision
      4. Fallback → Tesseract
    """

    def __init__(self):
        self.groq = GroqClient()

    SYSTEM_PROMPT = """You are an OCR and text extraction specialist for Indian steel industry documents.
The image contains a Request for Quotation (RFQ) from a steel buyer.
Documents may be handwritten, stamped, or printed in mixed Hindi-English.

Extract ALL text visible in the image. Do not interpret or classify — just extract.
Pay special attention to: numbers (dimensions, quantities), grade names (Fe 500, IS 2062),
and location names.

Return JSON: { "extracted_text": "...", "confidence": 0.0-1.0, "language_detected": "en|hi|gu|mixed" }
"""

    def _extract_pdf_text(self, file_path: str) -> tuple[str, int]:
        """Extract text from a PDF using pdfplumber. Returns (text, page_count)."""
        if not PDFPLUMBER_AVAILABLE:
            logger.warning("pdfplumber not installed, skipping text extraction")
            return "", 0

        try:
            all_text = ""
            page_count = 0
            with pdfplumber.open(file_path) as pdf:
                page_count = len(pdf.pages)
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    all_text += page_text + "\n"

                    # Also try to extract tables (common in formal RFQs)
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            if row:
                                cells = [str(c).strip() for c in row if c]
                                if cells:
                                    all_text += " | ".join(cells) + "\n"

            logger.info(f"pdfplumber extracted {len(all_text)} chars from {page_count} pages")
            return all_text.strip(), page_count
        except Exception as e:
            logger.error(f"pdfplumber extraction failed: {e}")
            return "", 0

    def _pdf_to_image(self, file_path: str) -> Optional[str]:
        """Convert first page of PDF to image for vision OCR."""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
            page = doc.load_page(0)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
            img_path = file_path.replace(".pdf", "_page0.png")
            pix.save(img_path)
            return img_path
        except ImportError:
            logger.warning("PyMuPDF not installed. Cannot convert PDF to image.")
            return None
        except Exception as e:
            logger.error(f"Failed to convert PDF to image: {e}")
            return None

    def preprocess_image(self, file_path: str) -> str:
        """Preprocess image for OCR."""
        from PIL import Image, ImageEnhance

        img = Image.open(file_path)
        # Convert to grayscale
        img = img.convert("L")
        # Increase contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)
        # Resize to min 1200px width
        if img.width < 1200:
            ratio = 1200 / img.width
            img = img.resize((1200, int(img.height * ratio)), Image.Resampling.LANCZOS)

        import os
        base, ext = os.path.splitext(file_path)
        preprocessed_path = f"{base}_preprocessed{ext}"
        img.save(preprocessed_path)
        return preprocessed_path

    def _vision_ocr(self, file_path: str) -> dict:
        """Run Groq Vision OCR on an image file."""
        preprocessed_path = self.preprocess_image(file_path)

        with open(preprocessed_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        result = self.groq.call_vision(
            system_prompt=self.SYSTEM_PROMPT,
            image_data=image_data,
            model="llama-3.2-11b-vision-preview"
        )

        if result.get("confidence", 0) < 0.5 and TESSERACT_AVAILABLE:
            result = self._tesseract_ocr(preprocessed_path)

        return result

    def run(self, ocr_input: OCRInput) -> OCROutput:
        """Run OCR on the input file.
        
        Strategy for PDFs:
          1. Try pdfplumber text extraction (works perfectly for typed/digital PDFs)
          2. If extracted text is <100 chars, treat as scanned → fall back to vision
        Strategy for images:
          1. Preprocess + Groq Vision
          2. Tesseract fallback
        """
        file_path = ocr_input.file_path

        # ========== PDF handling ==========
        if ocr_input.file_type.lower() == "pdf":
            # Step 1: Try direct text extraction (fast, no API cost)
            extracted_text, page_count = self._extract_pdf_text(file_path)

            if len(extracted_text) >= 100:
                # Text PDF — pdfplumber got good text. Done.
                logger.info(f"✅ PDF text extraction: {len(extracted_text)} chars, {page_count} pages")
                raw_text = self._post_process(extracted_text)
                return OCROutput(
                    raw_text=raw_text,
                    ocr_confidence=0.95,  # High confidence for direct text extraction
                    language_detected="en",
                    page_count=page_count
                )

            # Step 2: Scanned PDF — convert to image and use vision
            logger.info("PDF text extraction returned <100 chars, trying vision OCR...")
            img_path = self._pdf_to_image(file_path)
            if not img_path:
                return OCROutput(raw_text="", ocr_confidence=0.0, language_detected="en", page_count=0)

            file_path = img_path  # Fall through to image processing below

        # ========== Image handling ==========
        try:
            result = self._vision_ocr(file_path)
            raw_text = result.get("extracted_text", "")
            raw_text = self._post_process(raw_text)

            return OCROutput(
                raw_text=raw_text,
                ocr_confidence=result.get("confidence", 0.5),
                language_detected=result.get("language_detected", "en"),
                page_count=1
            )
        except Exception as e:
            logger.error(f"OCR failed: {e}. Returning empty result.")
            return OCROutput(
                raw_text="",
                ocr_confidence=0.0,
                language_detected="en",
                page_count=0
            )

    def _tesseract_ocr(self, file_path: str) -> dict:
        """Fallback OCR using Tesseract."""
        if not TESSERACT_AVAILABLE:
            return {"extracted_text": "", "confidence": 0.0, "language_detected": "en"}

        text = pytesseract.image_to_string(file_path, lang="eng+hin")
        return {
            "extracted_text": text,
            "confidence": 0.6,
            "language_detected": "mixed"
        }

    def _post_process(self, text: str) -> str:
        """Post-process extracted text."""
        import re
        # Normalize whitespace (but preserve newlines for table structure)
        lines = text.split("\n")
        cleaned = []
        for line in lines:
            line = " ".join(line.split())  # Collapse whitespace within each line
            if line.strip():
                cleaned.append(line)
        text = "\n".join(cleaned)
        # Fix specific steel grade OCR errors (context-aware only)
        # Do NOT globally replace 0 with O (destroys dimensions like "10mm")
        text = re.sub(r'Fe\s+([4-6])O([05D])', r'Fe \1\2', text)
        return text
