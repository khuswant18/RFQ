"""OCR Agent - Converts images/PDFs to clean, structured raw text."""
import base64
from typing import Optional
from pathlib import Path

from app.core.groq_client import GroqClient
from app.models.rfq import OCRInput, OCROutput

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


class OCRAgent:
    """
    OCR Agent: Converts image/PDF to clean, structured raw text.
    Handles blurry images, stamps, and mixed-language documents.
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

    def preprocess_image(self, file_path: str) -> str:
        """Preprocess image for OCR (placeholder for actual implementation)."""
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

        # Save preprocessed image
        preprocessed_path = file_path.replace(".", "_preprocessed.")
        img.save(preprocessed_path)
        return preprocessed_path

    def run(self, ocr_input: OCRInput) -> OCROutput:
        """Run OCR on the input file."""
        # Preprocess image
        preprocessed_path = self.preprocess_image(ocr_input.file_path)

        try:
            # Attempt 1: Groq Vision (base64 image)
            with open(preprocessed_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            result = self.groq.call_vision(
                system_prompt=self.SYSTEM_PROMPT,
                image_data=image_data,
                model="llama3-70b-8192"
            )

            if result.get("confidence", 0) < 0.5 and TESSERACT_AVAILABLE:
                # Attempt 2: Tesseract fallback
                result = self._tesseract_ocr(preprocessed_path)

            # Post-process (now selective, not global 0->O replacement)
            raw_text = result.get("extracted_text", "")
            raw_text = self._post_process(raw_text)

            return OCROutput(
                raw_text=raw_text,
                ocr_confidence=result.get("confidence", 0.5),
                language_detected=result.get("language_detected", "en"),
                page_count=1
            )
        except Exception as e:
            print(f"OCR failed: {e}. Returning empty result.")
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
        # Remove extra whitespace
        text = " ".join(text.split())
        # Fix specific steel grade OCR errors (context-aware only)
        # Do NOT globally replace 0 with O (destroys dimensions like "10mm")
        text = re.sub(r'Fe\s+([4-6])O([05D])', r'Fe \1\2', text)
        return text
