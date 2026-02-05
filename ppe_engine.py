import cv2
import os
from models import extra_yolo , ppe_model , PPE_CLASSES
from db import upsert_ppe_violation

PPE_DIR = "static/ppe/violations"
os.makedirs(PPE_DIR, exist_ok=True)

saved_persons = set()

PERSON_CLASS_ID = 0  # from yolo11n.pt

def run_ppe_on_frame(frame, camera_id=1):
    person_results = extra_yolo.track(frame, classes=[0], conf=0.5, persist=True, verbose=False)

    if not person_results or person_results[0].boxes is None:
        return frame

    boxes_obj = person_results[0].boxes

    if boxes_obj.xyxy is None or boxes_obj.id is None:
        return frame   # no tracked persons yet

    p_boxes = boxes_obj.xyxy.cpu().numpy()
    p_ids = boxes_obj.id.cpu().numpy()

    for (x1, y1, x2, y2), pid in zip(p_boxes, p_ids):
        x1, y1, x2, y2 = map(int, (x1, y1, x2, y2))
        pid = int(pid)

        person_crop = frame[y1:y2, x1:x2]

        # Save person image once
        img_path = f"{PPE_DIR}/person_{pid}.jpg"
        if pid not in saved_persons:
            cv2.imwrite(img_path, person_crop)
            saved_persons.add(pid)

        # 2. Run PPE model inside person crop
        ppe_results = ppe_model.predict(person_crop, conf=0.5, verbose=False)

        violations_found = []

        if ppe_results and ppe_results[0].boxes is not None:
            v_boxes = ppe_results[0].boxes.xyxy.cpu().numpy()
            v_classes = ppe_results[0].boxes.cls.cpu().numpy()

            for (vx1, vy1, vx2, vy2), vcls in zip(v_boxes, v_classes):
                vname = PPE_CLASSES[int(vcls)]

                if not vname.startswith("NO-"):
                    continue

                vx1, vy1, vx2, vy2 = map(int, (vx1, vy1, vx2, vy2))

                # Draw violation box (RED) on main frame
                cv2.rectangle(frame,
                              (x1 + vx1, y1 + vy1),
                              (x1 + vx2, y1 + vy2),
                              (0, 0, 255), 2)

                cv2.putText(frame, vname,
                            (x1 + vx1, y1 + vy1 - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

                violations_found.append(vname)

        # 3. Store merged violations
        if violations_found:
            for v in set(violations_found):
                upsert_ppe_violation(
                    person_id=pid,
                    violation=v,
                    person_image=img_path,
                    camera_id=camera_id
                )

        # Draw person box (GREEN)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0,255,0), 2)
        cv2.putText(frame, f"Person {pid}", (x1, y1-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

    return frame

def reset_ppe_tracker():
    global saved_persons
    saved_persons = set()  # reset saved person IDs

    try:
        if hasattr(extra_yolo, "predictor") and extra_yolo.predictor:
            extra_yolo.predictor.tracker = None
    except Exception:
        pass