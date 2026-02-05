from ultralytics import YOLO
from paddleocr import PaddleOCR
import cv2
import re

# ---------------- YOLO Models ----------------

# Vehicle detection / tracking
vehicle_model = YOLO("models/yolo11n.pt")

# Number plate detection
plate_model = YOLO("models/best.pt")

# PPE detection model (your renamed file)
ppe_model = YOLO("models/ppe_best.pt")

extra_yolo=YOLO("models/yolo11n(1).pt")
# PPE classes from your dataset
PPE_CLASSES = [
    'Hardhat', 'Mask', 'NO-Hardhat', 'NO-Mask',
    'NO-Safety Vest', 'Person', 'Safety Cone',
    'Safety Vest', 'machinery', 'vehicle'
]

# We will ignore these three
PPE_IGNORE = ['machinery', 'vehicle','Person']

# ---------------- PaddleOCR ----------------
ocr_reader = PaddleOCR(
    use_angle_cls=True,
    lang='en',
    use_gpu=False,
    enable_mkldnn=False
)

def ocr_plate(plate_img):
    if plate_img is None or plate_img.size == 0:
        return ""

    gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    gray = cv2.GaussianBlur(gray, (3,3), 0)

    result = ocr_reader.ocr(gray, cls=True)

    text = ""
    if result and result[0]:
        for line in result[0]:
            text += line[1][0]

    text = re.sub(r'[^A-Z0-9]', '', text.upper())
    return text