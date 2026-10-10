import cv2
import mediapipe as mp
import mediapipe.python.solutions.pose as mp_pose
import mediapipe.python.solutions.hands as mp_hands
import mediapipe.python.solutions.drawing_utils as mp_draw
import math
import os

CAMERA_INDEX = os.getenv('BODY_POINTING_CAMERA', '0')
try:
    if CAMERA_INDEX.isdigit():
        CAMERA_INDEX = int(CAMERA_INDEX)
except Exception:
    pass

MIRROR_CAMERA = True
SMOOTHING = 0.65
STABLE_FRAMES = 4

pose_detector = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=0,
    smooth_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

hand_detector = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    model_complexity=0,
    min_detection_confidence=0.45,
    min_tracking_confidence=0.55
)

import time

def run_body_pointing(timeout_seconds=20, camera_index=CAMERA_INDEX, mirror=MIRROR_CAMERA, show_window=True):
    """
    Runs MediPipe Pose & Hand detector to track index finger body pointing.
    Returns dict with keys: 'success', 'region', and optionally 'error'.
    """
    pose_detector = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=0,
        smooth_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    hand_detector = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        model_complexity=0,
        min_detection_confidence=0.45,
        min_tracking_confidence=0.55
    )

    cap = None
    try:
        cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            pose_detector.close()
            hand_detector.close()
            return {"success": False, "region": "unknown", "error": f"Could not open camera {camera_index}."}

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        smoothed_finger = None
        current_region = "Searching..."
        candidate_region = None
        candidate_count = 0

        start_time = time.time()
        final_region = "unknown"
        detected_stable = False

        print("Camera started.")
        print("Point with your index finger.")

        while True:
            if timeout_seconds and (time.time() - start_time) > timeout_seconds:
                break

            ret, frame = cap.read()
            if not ret:
                break

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pose_result = pose_detector.process(rgb)
            hand_result = hand_detector.process(rgb)
            detected_finger = None

            if hand_result.multi_hand_landmarks:
                best_distance = float("inf")
                for hand_landmarks in hand_result.multi_hand_landmarks:
                    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                    index_pip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_PIP]
                    wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]

                    tip_dist = math.hypot(index_tip.x - wrist.x, index_tip.y - wrist.y)
                    pip_dist = math.hypot(index_pip.x - wrist.x, index_pip.y - wrist.y)
                    pointing_score = tip_dist - pip_dist

                    if pointing_score > 0:
                        score = -pointing_score
                        if score < best_distance:
                            best_distance = score
                            detected_finger = (index_tip.x, index_tip.y)

            if detected_finger is None:
                smoothed_finger = None
                candidate_region = None
                candidate_count = 0
                current_region = "No finger detected"
            else:
                smoothed_finger = lerp(smoothed_finger, detected_finger, SMOOTHING)

            if pose_result.pose_landmarks is not None and smoothed_finger is not None:
                fx, fy = smoothed_finger
                new_region = classify_body_region(pose_result.pose_landmarks, fx, fy)

                if new_region == candidate_region:
                    candidate_count += 1
                else:
                    candidate_region = new_region
                    candidate_count = 1

                if candidate_count >= STABLE_FRAMES:
                    current_region = new_region
                    if current_region not in ("Searching...", "No finger detected", "unknown"):
                        final_region = current_region
                        detected_stable = True

            if show_window:
                if pose_result.pose_landmarks:
                    mp_draw.draw_landmarks(frame, pose_result.pose_landmarks, mp_pose.POSE_CONNECTIONS)

                if hand_result.multi_hand_landmarks:
                    for hand_landmarks in hand_result.multi_hand_landmarks:
                        mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                if smoothed_finger is not None:
                    h, w, _ = frame.shape
                    x = int(smoothed_finger[0] * w)
                    y = int(smoothed_finger[1] * h)
                    cv2.circle(frame, (x, y), 14, (0, 255, 0), -1)
                    cv2.circle(frame, (x, y), 20, (255, 255, 255), 2)

                display_frame = cv2.flip(frame, 1) if mirror else frame
                cv2.rectangle(display_frame, (10, 10), (700, 85), (0, 0, 0), -1)
                cv2.putText(display_frame, "POINTING AT:", (25, 42),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
                cv2.putText(display_frame, current_region.upper(), (220, 42),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
                cv2.putText(display_frame, "ESC = quit", (25, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

                cv2.imshow("Body Region Tracker", display_frame)
                if cv2.waitKey(1) & 0xFF == 27:
                    break

            if detected_stable and not show_window:
                break

        return {"success": True, "region": final_region}

    except Exception as e:
        return {"success": False, "region": "unknown", "error": str(e)}
    finally:
        if cap and cap.isOpened():
            cap.release()
        pose_detector.close()
        hand_detector.close()
        if show_window:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    result = run_body_pointing(timeout_seconds=None, show_window=True)
    print("Final Detected Region:", result)
