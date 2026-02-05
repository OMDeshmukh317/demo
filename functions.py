import re
from collections import defaultdict, Counter

# ---------------- Plate preprocessing ----------------
def preprocess_plate(text):
    """
    Cleans OCR text and validates it based on:
    - Starts with alphabet
    - Minimum length 8
    """
    if text is None:
        return None

    text = text.upper()
    text = re.sub(r'[^A-Z0-9]', '', text)

    if len(text) < 8:
        return None

    if not text[0].isalpha():
        return None

    return text

# ---------------- Buffers ----------------
def init_buffers():
    """
    Initializes buffers for first 5 frames per vehicle
    """
    plate_buffer = defaultdict(list)  # store first MAX_FRAMES OCR results per vehicle
    final_plate = {}                  # frozen plate per vehicle
    return plate_buffer, final_plate
