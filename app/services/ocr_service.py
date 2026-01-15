import re
import io
import numpy as np
from PIL import Image
import easyocr
from typing import Dict, Optional, Tuple


class OCRService:
    def __init__(self):
        # EasyOCR reader (CPU, English)
        self.reader = easyocr.Reader(["en"], gpu=False)

    # =====================================================
    # OCR TEXT EXTRACTION
    # =====================================================
    def extract_text(self, image_bytes: bytes) -> Tuple[str, float]:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        # ---- Resize for performance & stability ----
        max_width = 1200
        if image.width > max_width:
            ratio = max_width / image.width
            image = image.resize(
                (max_width, int(image.height * ratio)),
                Image.LANCZOS
            )

        image_np = np.array(image)

        results = self.reader.readtext(
            image_np,
            detail=1,
            paragraph=False,
            batch_size=8
        )

        if not results:
            return "", 0.0

        texts = [r[1] for r in results]
        confidences = [r[2] for r in results]

        full_text = "\n".join(texts)
        avg_confidence = sum(confidences) / len(confidences)

        return full_text, avg_confidence

    # =====================================================
    # FIELD EXTRACTION (HIGH ACCURACY – INDIA FOCUSED)
    # =====================================================
    def extract_fields(self, text: str) -> Dict[str, Optional[str]]:
        fields = {
            "name": None,
            "email": None,
            "phone": None,
            "aadhaar": None,
            "pan": None,
            "dob": None,
            "address": None,
            "state": None,
            "country": None
        }

        lines = [l.strip() for l in text.split("\n") if l.strip()]
        text_lower = text.lower()

        # ---------------- AADHAAR (PRIORITY) ----------------
        aadhaar_match = re.search(r'\b\d{4}\s?\d{4}\s?\d{4}\b', text)
        if aadhaar_match:
            fields["aadhaar"] = aadhaar_match.group().replace(" ", "")

        # ---------------- DOB (LABEL-AWARE) ----------------
        dob_match = re.search(
            r'(dob|date of birth|birth)[^\d]*(\d{2}[/-]\d{2}[/-]\d{4})',
            text_lower
        )
        if dob_match:
            fields["dob"] = dob_match.group(2)

        # ---------------- PAN ----------------
        pan_match = re.search(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', text)
        if pan_match:
            fields["pan"] = pan_match.group()

        # ---------------- EMAIL ----------------
        email_match = re.search(
            r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',
            text
        )
        if email_match:
            fields["email"] = email_match.group()

        # ---------------- PHONE ----------------
        phone_match = re.search(r'(\+91[\s-]?)?[6-9]\d{9}', text)
        if phone_match:
            fields["phone"] = phone_match.group()

        # ---------------- NAME (STRICT & SAFE) ----------------
        BLOCKLIST = [
            "government", "india", "department",
            "authority", "republic", "unique",
            "identification", "income", "tax"
        ]

        for line in lines:
            line_lower = line.lower()

            if (
                line.isupper()
                and 1 < len(line.split()) <= 3
                and not any(b in line_lower for b in BLOCKLIST)
                and not re.search(r'\d', line)
            ):
                fields["name"] = line.title()
                break

        # ---------------- ADDRESS ----------------
        for i, line in enumerate(lines):
            if any(k in line.lower() for k in [
                "address", "resident", "s/o", "c/o", "w/o"
            ]):
                fields["address"] = " ".join(lines[i:i+3])
                break

        # ---------------- COUNTRY / STATE ----------------
        if "india" in text_lower:
            fields["country"] = "India"

        STATES = [
            "delhi", "maharashtra", "karnataka",
            "tamil nadu", "uttar pradesh",
            "gujarat", "rajasthan"
        ]

        for s in STATES:
            if s in text_lower:
                fields["state"] = s.title()
                break

        return fields

    # =====================================================
    # DOCUMENT TYPE CLASSIFICATION (ID-FIRST)
    # =====================================================
    def categorize_document(self, fields: Dict[str, Optional[str]], text: str) -> str:
        text_lower = text.lower()

        if fields.get("aadhaar"):
            return "AADHAAR"
        if fields.get("pan"):
            return "PAN"
        if "voter" in text_lower:
            return "VOTER_ID"
        if "driving" in text_lower or "dl no" in text_lower:
            return "DRIVING_LICENCE"
        if fields.get("email") and fields.get("phone"):
            return "BUSINESS_CARD"

        return "GENERIC_DOCUMENT"


# Singleton instance
ocr_service = OCRService()
