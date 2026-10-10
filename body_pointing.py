import cv2
import mediapipe as mp
import mediapipe.python.solutions.pose as mp_pose
import mediapipe.python.solutions.hands as mp_hands
import mediapipe.python.solutions.drawing_utils as mp_draw
import math
import os
import time
import warnings

# Silence the noisy protobuf deprecation warning
warnings.filterwarnings("ignore", category=UserWarning, module="google.protobuf")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CAMERA_INDEX = os.getenv('BODY_POINTING_CAMERA', '0')
try:
    if isinstance(CAMERA_INDEX, str) and CAMERA_INDEX.isdigit():
        CAMERA_INDEX = int(CAMERA_INDEX)
except Exception:
    pass

MIRROR_CAMERA  = True
SMOOTHING      = 0.65   # 0 = no smoothing, 1 = frozen
STABLE_FRAMES  = 4      # frames a region must persist before locking in

PL = mp_pose.PoseLandmark
HL = mp_hands.HandLandmark


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def lerp(a, b, t):
    """Linear interpolation between two (x, y) tuples. None-safe."""
    if a is None:
        return b
    if b is None:
        return a
    return (a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t)


def _mid(lm, i, j):
    """Midpoint of two landmarks in normalized coords."""
    a, b = lm[i], lm[j]
    return ((a.x + b.x) / 2.0, (a.y + b.y) / 2.0)


def _dist(p, q):
    return math.hypot(p[0] - q[0], p[1] - q[1])


def _point_segment_dist(p, a, b):
    """Distance from point p to segment a-b (all in normalized coords)."""
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return _dist(p, a)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    proj = (ax + t * dx, ay + t * dy)
    return _dist(p, proj)


def classify_body_region(pose_landmarks, fx, fy):
    """
    Detailed body-region classifier.

    Returns a tuple: (region_label, detail_dict)

    region_label is a human-readable string. detail_dict contains the
    nearest landmark, distance, side, and segment name for debugging / UI.
    """
    lm = pose_landmarks.landmark
    p = (fx, fy)

    # -------------------------------------------------------------------
    # Key anchor points (all normalized 0..1)
    # -------------------------------------------------------------------
    nose       = lm[PL.NOSE]
    l_eye      = lm[PL.LEFT_EYE]
    r_eye      = lm[PL.RIGHT_EYE]
    l_ear      = lm[PL.LEFT_EAR]
    r_ear      = lm[PL.RIGHT_EAR]
    l_shoulder = lm[PL.LEFT_SHOULDER]
    r_shoulder = lm[PL.RIGHT_SHOULDER]
    l_elbow    = lm[PL.LEFT_ELBOW]
    r_elbow    = lm[PL.RIGHT_ELBOW]
    l_wrist    = lm[PL.LEFT_WRIST]
    r_wrist    = lm[PL.RIGHT_WRIST]
    l_hip      = lm[PL.LEFT_HIP]
    r_hip      = lm[PL.RIGHT_HIP]
    l_knee     = lm[PL.LEFT_KNEE]
    r_knee     = lm[PL.RIGHT_KNEE]
    l_ankle    = lm[PL.LEFT_ANKLE]
    r_ankle    = lm[PL.RIGHT_ANKLE]
    l_foot     = lm[PL.LEFT_FOOT_INDEX]
    r_foot     = lm[PL.RIGHT_FOOT_INDEX]

    # -------------------------------------------------------------------
    # Reference bands
    # -------------------------------------------------------------------
    shoulder_y = (l_shoulder.y + r_shoulder.y) / 2
    hip_y      = (l_hip.y + r_hip.y) / 2
    knee_y     = (l_knee.y + r_knee.y) / 2
    ankle_y    = (l_ankle.y + r_ankle.y) / 2
    mid_x      = (l_shoulder.x + r_shoulder.x + l_hip.x + r_hip.x) / 4.0

    # Which side of the body (subject's left/right) is the finger on?
    subject_side = "left" if fx < mid_x else "right"

    # -------------------------------------------------------------------
    # 1) HEAD-zone check (above shoulders). Split into eyes / ears / mouth /
    #    nose / forehead / chin based on landmark distances.
    # -------------------------------------------------------------------
    if fy < shoulder_y:
        head_landmarks = {
            "nose":         nose,
            "left_eye":     l_eye,
            "right_eye":    r_eye,
            "left_ear":     l_ear,
            "right_ear":    r_ear,
        }
        # Nearest head landmark
        nearest_name, nearest_lm = min(
            head_landmarks.items(), key=lambda kv: _dist(p, (kv[1].x, kv[1].y))
        )
        d_head = _dist(p, (nearest_lm.x, nearest_lm.y))

        # Eye/nose radius (normalized) — tune to your resolution
        if d_head < 0.04:
            if nearest_name == "nose":
                return ("head: nose", {"landmark": "nose", "dist": d_head,
                                       "side": subject_side})
            if "eye" in nearest_name:
                return (f"head: {nearest_name.replace('_', ' ')}",
                        {"landmark": nearest_name, "dist": d_head,
                         "side": subject_side})
            if "ear" in nearest_name:
                return (f"head: {nearest_name.replace('_', ' ')}",
                        {"landmark": nearest_name, "dist": d_head,
                         "side": subject_side})

        # Otherwise just say head, with a hint about what's nearby
        return (f"head ({nearest_name.replace('_', ' ')})",
                {"landmark": nearest_name, "dist": d_head,
                 "side": subject_side})

    # -------------------------------------------------------------------
    # 2) ARM checks — compare distance to each arm's upper/lower segments
    #    and to the wrist/hand region. Do this BEFORE torso fallback so a
    #    finger clearly on an arm is labeled arm, not torso.
    # -------------------------------------------------------------------
    arm_candidates = []

    # Left arm segments
    arm_candidates.append(("left shoulder",       (l_shoulder.x, l_shoulder.y)))
    arm_candidates.append(("left upper arm",      None))  # placeholder, segment below
    arm_candidates.append(("left elbow",          (l_elbow.x, l_elbow.y)))
    arm_candidates.append(("left forearm",        None))
    arm_candidates.append(("left wrist",          (l_wrist.x, l_wrist.y)))

    # Right arm
    arm_candidates.append(("right shoulder",      (r_shoulder.x, r_shoulder.y)))
    arm_candidates.append(("right upper arm",     None))
    arm_candidates.append(("right elbow",         (r_elbow.x, r_elbow.y)))
    arm_candidates.append(("right forearm",       None))
    arm_candidates.append(("right wrist",         (r_wrist.x, r_wrist.y)))

    # Segment-based distances (upper arm = shoulder->elbow, forearm = elbow->wrist)
    seg_defs = [
        ("left upper arm",  (l_shoulder.x, l_shoulder.y), (l_elbow.x, l_elbow.y)),
        ("left forearm",    (l_elbow.x,    l_elbow.y),    (l_wrist.x, l_wrist.y)),
        ("right upper arm", (r_shoulder.x, r_shoulder.y), (r_elbow.x, r_elbow.y)),
        ("right forearm",   (r_elbow.x,    r_elbow.y),    (r_wrist.x, r_wrist.y)),
    ]

    best_arm = None  # (dist, label)
    for name, a, b in seg_defs:
        d = _point_segment_dist(p, a, b)
        if best_arm is None or d < best_arm[0]:
            best_arm = (d, name)

    # Point-landmark arm candidates (shoulder/elbow/wrist)
    for name, pt in arm_candidates:
        if pt is None:
            continue
        d = _dist(p, pt)
        if best_arm is None or d < best_arm[0]:
            best_arm = (d, name)

    # Arm threshold (normalized). ~0.06 covers a reasonably thick arm.
    ARM_RADIUS = 0.07

    # -------------------------------------------------------------------
    # 3) LEG checks
    # -------------------------------------------------------------------
    seg_defs_leg = [
        ("left thigh",      (l_hip.x, l_hip.y),   (l_knee.x, l_knee.y)),
        ("left shin",       (l_knee.x, l_knee.y), (l_ankle.x, l_ankle.y)),
        ("right thigh",     (r_hip.x, r_hip.y),   (r_knee.x, r_knee.y)),
        ("right shin",      (r_knee.x, r_knee.y), (r_ankle.x, r_ankle.y)),
    ]
    best_leg = None
    for name, a, b in seg_defs_leg:
        d = _point_segment_dist(p, a, b)
        if best_leg is None or d < best_leg[0]:
            best_leg = (d, name)

    # Also check hips/knees/ankles/feet as point features
    leg_points = [
        ("left hip",    (l_hip.x,   l_hip.y)),
        ("right hip",   (r_hip.x,   r_hip.y)),
        ("left knee",   (l_knee.x,  l_knee.y)),
        ("right knee",  (r_knee.x,  r_knee.y)),
        ("left ankle",  (l_ankle.x, l_ankle.y)),
        ("right ankle", (r_ankle.x, r_ankle.y)),
        ("left foot",   (l_foot.x,  l_foot.y)),
        ("right foot",  (r_foot.x,  r_foot.y)),
    ]
    for name, pt in leg_points:
        d = _dist(p, pt)
        if best_leg is None or d < best_leg[0]:
            best_leg = (d, name)

    LEG_RADIUS = 0.07

    # -------------------------------------------------------------------
    # 4) Torso fallback — decide between arms, legs, and torso by nearest
    #    of the three, then subdivide the torso.
    # -------------------------------------------------------------------
    # If arm is clearly closest and within radius, prefer it
    if best_arm and best_arm[0] < ARM_RADIUS and \
       (not best_leg or best_arm[0] <= best_leg[0]):
        return (best_arm[1],
                {"segment": best_arm[1], "dist": best_arm[0],
                 "side": subject_side})

    if best_leg and best_leg[0] < LEG_RADIUS and \
       (not best_arm or best_leg[0] < best_arm[0]):
        return (best_leg[1],
                {"segment": best_leg[1], "dist": best_leg[0],
                 "side": subject_side})

    # Otherwise, we're inside the torso. Subdivide.
    # Vertical subdivision of the torso between shoulder_y and hip_y.
    torso_top    = shoulder_y
    torso_bottom = hip_y
    torso_h      = max(1e-6, torso_bottom - torso_top)
    rel_y        = (fy - torso_top) / torso_h   # 0 at shoulders, 1 at hips

    if rel_y < 0.30:
        band = "upper chest"
    elif rel_y < 0.65:
        band = "mid torso"
    else:
        band = "lower abdomen"

    # Horizontal subdivision
    left_x  = (l_shoulder.x + l_hip.x) / 2.0
    right_x = (r_shoulder.x + r_hip.x) / 2.0

    # Sternum region — between shoulders, middle band
    sternum_x = (l_shoulder.x + r_shoulder.x) / 2.0
    if abs(fx - sternum_x) < 0.05 and rel_y < 0.55:
        side_label = "center"
    else:
        side_label = subject_side

    label = f"{side_label} {band}"
    return (label,
            {"band": band, "side": side_label, "rel_y": rel_y,
             "mid_x": mid_x})


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def run_body_pointing(timeout_seconds=20,
                      camera_index=CAMERA_INDEX,
                      mirror=MIRROR_CAMERA,
                      show_window=True):
    """
    Track index-finger pointing at body regions.

    Returns dict: {'success': bool, 'region': str, 'detail': dict|None,
                   'error': str|None}
    """
    pose_detector = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=0,
        smooth_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    hand_detector = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        model_complexity=0,
        min_detection_confidence=0.45,
        min_tracking_confidence=0.55,
    )

    cap = None
    try:
        cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            return {"success": False, "region": "unknown", "detail": None,
                    "error": f"Could not open camera {camera_index}."}

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        smoothed_finger  = None
        current_region   = "Searching..."
        current_detail   = None
        candidate_region = None
        candidate_count  = 0

        start_time    = time.time()
        final_region  = "unknown"
        final_detail  = None
        detected_stable = False

        print("Camera started.")
        print("Point with your index finger. Press ESC to quit.")

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

            # ---------------- Pick the "pointing" hand ----------------
            if hand_result.multi_hand_landmarks:
                best_score = -float("inf")
                for hand_landmarks in hand_result.multi_hand_landmarks:
                    index_tip = hand_landmarks.landmark[HL.INDEX_FINGER_TIP]
                    index_pip = hand_landmarks.landmark[HL.INDEX_FINGER_PIP]
                    wrist     = hand_landmarks.landmark[HL.WRIST]

                    tip_dist = math.hypot(index_tip.x - wrist.x,
                                          index_tip.y - wrist.y)
                    pip_dist = math.hypot(index_pip.x - wrist.x,
                                          index_pip.y - wrist.y)
                    pointing_score = tip_dist - pip_dist

                    if pointing_score > 0 and pointing_score > best_score:
                        best_score = pointing_score
                        detected_finger = (index_tip.x, index_tip.y)

            # ---------------- Smooth the finger position ---------------
            if detected_finger is None:
                smoothed_finger  = None
                candidate_region = None
                candidate_count  = 0
                current_region   = "No finger detected"
                current_detail   = None
            else:
                smoothed_finger = lerp(smoothed_finger, detected_finger, SMOOTHING)

            # ---------------- Classify body region ---------------------
            if pose_result.pose_landmarks is not None and smoothed_finger is not None:
                fx, fy = smoothed_finger
                new_region, new_detail = classify_body_region(
                    pose_result.pose_landmarks, fx, fy
                )

                if new_region == candidate_region:
                    candidate_count += 1
                else:
                    candidate_region = new_region
                    candidate_count  = 1
                    current_detail   = new_detail

                if candidate_count >= STABLE_FRAMES:
                    current_region = new_region
                    if current_region not in ("Searching...",
                                              "No finger detected", "unknown"):
                        final_region = current_region
                        final_detail = new_detail
                        detected_stable = True

            # ---------------- Draw overlay -----------------------------
            if show_window:
                if pose_result.pose_landmarks:
                    mp_draw.draw_landmarks(
                        frame, pose_result.pose_landmarks, mp_pose.POSE_CONNECTIONS
                    )
                if hand_result.multi_hand_landmarks:
                    for hand_landmarks in hand_result.multi_hand_landmarks:
                        mp_draw.draw_landmarks(
                            frame, hand_landmarks, mp_hands.HAND_CONNECTIONS
                        )

                if smoothed_finger is not None:
                    h, w, _ = frame.shape
                    x = int(smoothed_finger[0] * w)
                    y = int(smoothed_finger[1] * h)
                    cv2.circle(frame, (x, y), 14, (0, 255, 0), -1)
                    cv2.circle(frame, (x, y), 20, (255, 255, 255), 2)

                display_frame = cv2.flip(frame, 1) if mirror else frame

                # Top info panel
                cv2.rectangle(display_frame, (10, 10), (900, 130), (0, 0, 0), -1)
                cv2.putText(display_frame, "POINTING AT:", (25, 42),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
                cv2.putText(display_frame, current_region.upper(), (220, 42),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)

                # Detail line (if any)
                if current_detail:
                    detail_str = ", ".join(
                        f"{k}={v:.3f}" if isinstance(v, float) else f"{k}={v}"
                        for k, v in current_detail.items()
                    )
                    cv2.putText(display_frame, detail_str[:110], (25, 75),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 220, 255), 1)

                cv2.putText(display_frame, "ESC = quit", (25, 115),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

                cv2.imshow("Body Region Tracker", display_frame)
                if cv2.waitKey(1) & 0xFF == 27:
                    break

            if detected_stable and not show_window:
                break

        return {"success": True, "region": final_region,
                "detail": final_detail, "error": None}

    except Exception as e:
        return {"success": False, "region": "unknown",
                "detail": None, "error": str(e)}
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