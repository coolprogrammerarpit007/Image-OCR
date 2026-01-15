import re
from datetime import datetime
import io
from typing import Dict, Optional, Tuple
from PIL import Image
import numpy as np
import easyocr

class OCRService:
    def __init__(self):
        # English only (fast & accurate for cards)
        self.reader = easyocr.Reader(
            ['en'],
            gpu=False
        )

    def extract_text(self, image_bytes: bytes) -> Tuple[str, float]:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image_np = np.array(image)

        results = self.reader.readtext(image_np)

        if not results:
            return "", 0.0

        texts = [res[1] for res in results]
        confidences = [res[2] for res in results]

        full_text = "\n".join(texts)
        avg_confidence = sum(confidences) / len(confidences)

        return full_text, avg_confidence

    
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

        # Email
        m = re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', text)
        if m:
            fields["email"] = m.group()

        # Phone / Mobile
        m = re.search(r'\b[6-9]\d{9}\b', text)
        if m:
            fields["phone"] = m.group()

        # Aadhaar
        m = re.search(r'\b\d{4}\s?\d{4}\s?\d{4}\b', text)
        if m:
            fields["aadhaar"] = m.group().replace(" ", "")

        # PAN
        m = re.search(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', text)
        if m:
            fields["pan"] = m.group()

        # Name (best effort for cards)
        for line in lines[:6]:
            if line.isupper() and 3 < len(line) < 40:
                if not any(x in line for x in ["GOVERNMENT", "INDIA", "INCOME", "TAX"]):
                    fields["name"] = line.title()
                    break

        # Address
        for i, line in enumerate(lines):
            if any(k in line.lower() for k in ["address", "resident", "s/o", "c/o"]):
                fields["address"] = " ".join(lines[i:i+4])
                break

        # Country & State (basic)
        if "india" in text_lower:
            fields["country"] = "India"

        states = [
            "maharashtra", "delhi", "karnataka",
            "tamil nadu", "uttar pradesh",
            "gujarat", "rajasthan"
        ]
        for s in states:
            if s in text_lower:
                fields["state"] = s.title()
                fields["country"] = "India"
                break

        return fields


    def extract_fields(self, text: str):
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

        # ---------- EMAIL ----------
        m = re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', text)
        if m:
            fields["email"] = m.group()

        # ---------- PHONE ----------
        m = re.search(r'\b[6-9]\d{9}\b', text)
        if m:
            fields["phone"] = m.group()

        # ---------- AADHAAR ----------
        m = re.search(r'\b\d{4}\s?\d{4}\s?\d{4}\b', text)
        if m:
            fields["aadhaar"] = m.group().replace(" ", "")

        # ---------- PAN ----------
        m = re.search(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', text)
        if m:
            fields["pan"] = m.group()

        # ---------- DOB ----------
        dob_patterns = [
            r'\b(\d{2}[/-]\d{2}[/-]\d{4})\b',   # 12/05/1998
            r'\b(\d{4}[/-]\d{2}[/-]\d{2})\b',   # 1998-05-12
            r'\b(\d{2}\.\d{2}\.\d{4})\b'        # 12.05.1998
        ]

        for line in lines:
            if any(k in line.lower() for k in ["dob", "date of birth", "d.o.b"]):
                for p in dob_patterns:
                    m = re.search(p, line)
                    if m:
                        fields["dob"] = self._normalize_dob(m.group())
                        break

        # fallback: date without label (PAN / ID cards)
        if not fields["dob"]:
            for p in dob_patterns:
                m = re.search(p, text)
                if m:
                    fields["dob"] = self._normalize_dob(m.group())
                    break

        # ---------- NAME ----------
        for line in lines[:6]:
            if line.isupper() and 3 < len(line) < 40:
                if not any(x in line for x in ["GOVERNMENT", "INDIA", "INCOME", "TAX"]):
                    fields["name"] = line.title()
                    break

        # ---------- ADDRESS ----------
        for i, line in enumerate(lines):
            if any(k in line.lower() for k in ["address", "resident", "s/o", "c/o"]):
                fields["address"] = " ".join(lines[i:i+4])
                break

        # ---------- COUNTRY & STATE ----------
        if "india" in text_lower:
            fields["country"] = "India"

        states = [
            "maharashtra", "delhi", "karnataka",
            "tamil nadu", "uttar pradesh",
            "gujarat", "rajasthan"
        ]
        for s in states:
            if s in text_lower:
                fields["state"] = s.title()
                fields["country"] = "India"
                break

        return fields
    
    
    def _normalize_dob(self, dob_str: str):
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y"):
            try:
                return datetime.strptime(dob_str, fmt).date()
            except ValueError:
                continue
        return None

    def categorize_document(self, fields: Dict[str, Optional[str]], text: str) -> str:
        t = text.lower()

        if fields.get("aadhaar"):
            return "AADHAAR"
        if fields.get("pan"):
            return "PAN"
        if "voter" in t:
            return "VOTER_ID"
        if "driving" in t or "dl no" in t:
            return "DRIVING_LICENCE"
        if fields.get("email") and fields.get("phone"):
            return "BUSINESS_CARD"
        if "happy birthday" in t or "congratulations" in t:
            return "GREETING_CARD"
        if "school" in t or "college" in t:
            return "EDUCATIONAL_ID"

        return "GENERIC_ID"


ocr_service = OCRService()
