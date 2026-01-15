import pytesseract
from PIL import Image
import re

def extract_text(image_path: str) -> dict:
    text = pytesseract.image_to_string(Image.open(image_path))

    return {
        "name": extract_name(text),
        "mobile": extract_mobile(text),
        "aadhaar": extract_aadhaar(text),
        "pan": extract_pan(text),
        "address": extract_address(text),
        "raw_text": text
    }

def extract_mobile(text):
    match = re.search(r'[6-9]\d{9}', text)
    return match.group() if match else None

def extract_aadhaar(text):
    match = re.search(r'\d{4}\s\d{4}\s\d{4}', text)
    return match.group() if match else None

def extract_pan(text):
    match = re.search(r'[A-Z]{5}[0-9]{4}[A-Z]', text)
    return match.group() if match else None

def extract_name(text):
    lines = text.split('\n')
    for line in lines:
        if line.isalpha() and len(line) > 3:
            return line
    return None

def extract_address(text):
    return text[:300]  # simple fallback
