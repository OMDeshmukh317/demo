import cv2
import os
from collections import Counter

from models import vehicle_model, plate_model, ocr_plate
from functions import preprocess_plate, init_buffers
from db import insert_anpr_event

# ---------------- Image storage paths ----------------
VEHICLE_DIR = "static/anpr/vehicles"
PLATE_DIR = "static/anpr/plates"
os.makedirs(VEHICLE_DIR, exist_ok=True)
os.makedirs(PLATE_DIR, exist_ok=True)

# ---------------- Buffers ----------------
plate_buffer, final_plate = init_buffers()
MAX_FRAMES = 5
saved_tracks = set()

# ---------------- Main Function ----------------
def run_anpr_on_frame(frame, camera_id=1):
    results = vehicle_model.track(
        frame,
        conf=0.4,
        classes=[2, 3, 5, 7],  # car, motorcycle, bus, truck
        persist=True,
        verbose=False
    )

    if results and results[0].boxes is not None and results[0].boxes.id is not None:
        boxes = results[0].boxes.xyxy.cpu().numpy()
        ids = results[0].boxes.id.cpu().numpy()

        for box, track_id in zip(boxes, ids):
            x1, y1, x2, y2 = map(int, box)
            vid = int(track_id)

            vehicle_crop = frame[y1:y2, x1:x2]

            # ---------------- Draw vehicle box ----------------
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.putText(
                frame, f"ID {vid}", (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2
            )

            # ---------------- Plate detection ----------------
            plate_results = plate_model.predict(
                vehicle_crop, conf=0.4, verbose=False
            )

            if plate_results[0].boxes is None:
                continue

            for pbox in plate_results[0].boxes.xyxy.cpu().numpy():
                px1, py1, px2, py2 = map(int, pbox)
                plate_crop = vehicle_crop[py1:py2, px1:px2]

                raw_text = ocr_plate(plate_crop)
                clean_text = preprocess_plate(raw_text)

                # 🚨 IMPORTANT FIX:
                # If text is invalid (<8 chars or fails rules),
                # treat it as NOT A NUMBER PLATE
                if clean_text is None:
                    continue

                # ---------------- Buffer Logic ----------------
                if vid not in final_plate:
                    plate_buffer[vid].append(clean_text)

                    # Freeze plate after MAX_FRAMES OR single-frame case
                    if (
                        len(plate_buffer[vid]) >= MAX_FRAMES
                        or (len(plate_buffer[vid]) == 1 and vid not in saved_tracks)
                    ):
                        final_plate[vid] = Counter(
                            plate_buffer[vid]
                        ).most_common(1)[0][0]

                        if vid not in saved_tracks:
                            vehicle_path = f"{VEHICLE_DIR}/vehicle_{vid}.jpg"
                            plate_path = f"{PLATE_DIR}/plate_{vid}.jpg"

                            cv2.imwrite(vehicle_path, vehicle_crop)
                            cv2.imwrite(plate_path, plate_crop)

                            insert_anpr_event(
                                track_id=vid,
                                plate_number=final_plate[vid],
                                vehicle_image=vehicle_path,
                                plate_image=plate_path,
                                camera_id=camera_id
                            )

                            saved_tracks.add(vid)

                # ---------------- Display Text ----------------
                display_text = final_plate[vid] if vid in final_plate else "Detecting..."

                # ---------------- Draw plate box ----------------
                cv2.rectangle(
                    frame,
                    (x1 + px1, y1 + py1),
                    (x1 + px2, y1 + py2),
                    (0, 255, 0), 2
                )

                cv2.putText(
                    frame,
                    display_text,
                    (x1 + px1, y1 + py1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2
                )

    return frame