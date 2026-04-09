"""
attendance_engine.py
--------------------
Handles the camera stream, face recognition, and attendance marking.
Imported by app.py.  Can also mark attendance to both DB and daily CSV.
Uses db.py for database connections (PostgreSQL or SQLite).
"""

import cv2
import face_recognition
import numpy as np
import pickle
import csv
import os
import threading
import logging
from datetime import date, datetime
from collections import defaultdict

from db import get_db, USE_PG

logger = logging.getLogger('smartattend.engine')

# ── Detection model: prefer CNN for accuracy, fallback to HOG ────────────────
try:
    import dlib
    _HAS_CNN = dlib.DLIB_USE_CUDA or os.path.exists(
        os.path.join(os.path.dirname(dlib.__file__), 'mmod_human_face_detector.dat')
    )
except Exception:
    _HAS_CNN = False

DETECTION_MODEL = 'cnn' if _HAS_CNN else 'hog'
logger.info(f'Face detection model: {DETECTION_MODEL}')


class AttendanceEngine:
    # ── Tuning constants ──────────────────────────────────────────────────────
    FRAME_SCALE       = 0.5      # 50% scale (was 0.25 — too aggressive)
    MATCH_TOLERANCE   = 0.55     # distance threshold (0.6 = default, 0.50 was too strict)
    NUM_JITTERS       = 2        # jitters for encoding (more = more robust, slower)
    MIN_FACE_WIDTH    = 40       # minimum face width in pixels (at scaled resolution)
    CONFIRM_FRAMES    = 2        # require N consecutive frames before marking

    def __init__(self, encodings_path: str, db_path: str, attendance_dir: str):
        self.encodings_path  = encodings_path
        self.db_path         = db_path
        self.attendance_dir  = attendance_dir

        self.known_data      = self._load_encodings()
        self.video           = None
        self._lock           = threading.Lock()
        self._marked_today   : set = set()
        self._pending_marks  : dict = {}  # student_id → consecutive frame count

        os.makedirs(attendance_dir, exist_ok=True)
        logger.info(f'Engine loaded with {len(self.known_data["encodings"])} encodings')

    # ── Encodings ─────────────────────────────────────────────────────────────
    def _load_encodings(self) -> dict:
        """Load face encodings from DB (PostgreSQL) or pickle file (local)."""
        try:
            conn = get_db(self.db_path)
            rows = conn.execute(
                'SELECT student_id, name, encoding FROM face_encodings'
            ).fetchall()
            conn.close()

            if rows:
                data = {'encodings': [], 'ids': [], 'names': []}
                for row in rows:
                    enc = np.frombuffer(bytes(row['encoding']), dtype=np.float64)
                    data['encodings'].append(enc)
                    data['ids'].append(row['student_id'])
                    data['names'].append(row['name'])
                return data
        except Exception:
            pass  # Table might not exist yet on first run

        # Fallback to pickle file (local dev)
        if os.path.exists(self.encodings_path):
            with open(self.encodings_path, 'rb') as f:
                return pickle.load(f)

        return {'encodings': [], 'ids': [], 'names': []}

    def reload_encodings(self):
        """Call after registering a new student so camera picks up the change."""
        self.known_data = self._load_encodings()

    def save_encodings(self):
        """Save to pickle file (local cache)."""
        os.makedirs(os.path.dirname(self.encodings_path), exist_ok=True)
        with open(self.encodings_path, 'wb') as f:
            pickle.dump(self.known_data, f)

    def add_encoding(self, student_id: str, name: str, encoding):
        """Append a single encoding, persist to DB and local pickle."""
        self.known_data['encodings'].append(encoding)
        self.known_data['ids'].append(student_id)
        self.known_data['names'].append(name)

        # Save to database
        try:
            conn = get_db(self.db_path)
            conn.execute(
                'INSERT INTO face_encodings (student_id, name, encoding) VALUES (?, ?, ?)',
                (student_id, name, encoding.tobytes())
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f'[ENGINE] Warning: could not save encoding to DB: {e}')

        # Also save to pickle as local cache
        try:
            self.save_encodings()
        except Exception:
            pass

    def remove_encoding(self, student_id: str):
        """Remove all encodings for a student from memory, DB, and pickle."""
        indices = [i for i, sid in enumerate(self.known_data['ids'])
                   if sid == student_id]
        for i in reversed(indices):
            self.known_data['encodings'].pop(i)
            self.known_data['ids'].pop(i)
            self.known_data['names'].pop(i)

        # Remove from database
        try:
            conn = get_db(self.db_path)
            conn.execute('DELETE FROM face_encodings WHERE student_id=?', (student_id,))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f'[ENGINE] Warning: could not remove encoding from DB: {e}')

        try:
            self.save_encodings()
        except Exception:
            pass

    # ── Camera ────────────────────────────────────────────────────────────────
    def open_camera(self, index: int = 0):
        if self.video is None or not self.video.isOpened():
            self.video = cv2.VideoCapture(index)
            self._marked_today.clear()

    def close_camera(self):
        if self.video and self.video.isOpened():
            self.video.release()
        self.video = None

    # ── Attendance ────────────────────────────────────────────────────────────
    def mark_attendance(self, student_id: str, name: str) -> bool:
        """
        Mark a student present for today.
        Returns True if newly marked, False if already marked.
        """
        if student_id in self._marked_today:
            return False

        today = date.today().isoformat()
        now   = datetime.now().strftime('%H:%M:%S')

        with self._lock:
            conn = get_db(self.db_path)
            existing = conn.execute(
                'SELECT 1 FROM attendance WHERE student_id=? AND date=?',
                (student_id, today)
            ).fetchone()

            if not existing:
                conn.execute(
                    'INSERT INTO attendance (student_id, name, date, time, status) '
                    'VALUES (?,?,?,?,?)',
                    (student_id, name, today, now, 'Present')
                )
                conn.commit()
                self._marked_today.add(student_id)
                self._append_csv(student_id, name, today, now)

            conn.close()
            return not bool(existing)

    def _append_csv(self, student_id: str, name: str, today: str, now: str):
        csv_path   = os.path.join(self.attendance_dir, f'attendance_{today}.csv')
        new_file   = not os.path.exists(csv_path)
        try:
            with open(csv_path, 'a', newline='') as f:
                writer = csv.writer(f)
                if new_file:
                    writer.writerow(['Student ID', 'Name', 'Date', 'Time', 'Status'])
                writer.writerow([student_id, name, today, now, 'Present'])
        except Exception:
            pass  # CSV is optional, DB is the source of truth

    # ── Image preprocessing ────────────────────────────────────────────────────
    @staticmethod
    def _preprocess_frame(rgb_image):
        """
        Apply histogram equalisation to the luminance channel
        so face recognition works better under varied lighting.
        """
        lab = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        lab = cv2.merge([l, a, b])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

    def _match_face(self, face_encoding):
        """
        Match a face encoding against known data using per-student
        average-distance voting.  Returns (student_id, name, confidence)
        or (None, None, 0).
        """
        if not self.known_data['encodings']:
            return None, None, 0

        distances = face_recognition.face_distance(
            self.known_data['encodings'], face_encoding
        )

        # Group distances by student_id and pick the best average
        student_dists = defaultdict(list)
        for i, dist in enumerate(distances):
            sid = self.known_data['ids'][i]
            student_dists[sid].append(dist)

        best_sid  = None
        best_dist = float('inf')
        for sid, dists in student_dists.items():
            # Use the minimum distance among all encodings for this student
            min_dist = min(dists)
            if min_dist < best_dist:
                best_dist = min_dist
                best_sid  = sid

        if best_dist > self.MATCH_TOLERANCE:
            return None, None, 0

        # Look up the name for the best match
        idx  = self.known_data['ids'].index(best_sid)
        name = self.known_data['names'][idx]
        confidence = max(0, 1 - best_dist)
        return best_sid, name, confidence

    # ── Frame processing ──────────────────────────────────────────────────────
    def get_frame(self) -> bytes | None:
        if not self.video or not self.video.isOpened():
            return None

        ok, frame = self.video.read()
        if not ok:
            return None

        scale      = self.FRAME_SCALE
        inv_scale  = int(1 / scale)

        # Downscale for faster recognition (50% instead of 25%)
        small     = cv2.resize(frame, (0, 0), fx=scale, fy=scale)
        rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        # Preprocessing: equalise lighting
        rgb_small = self._preprocess_frame(rgb_small)

        locations = face_recognition.face_locations(rgb_small, model=DETECTION_MODEL)
        encs      = face_recognition.face_encodings(rgb_small, locations,
                                                     num_jitters=1)  # 1 jitter during live feed for speed

        seen_students = set()  # track which students we see this frame

        for enc, loc in zip(encs, locations):
            top, right, bottom, left = loc

            # Skip faces that are too small (likely far away or noise)
            face_w = right - left
            face_h = bottom - top
            if face_w < self.MIN_FACE_WIDTH or face_h < self.MIN_FACE_WIDTH:
                continue

            label      = 'Unknown'
            student_id = None
            color      = (0, 0, 220)   # red = unknown
            conf       = 0

            student_id, label, conf = self._match_face(enc)

            if student_id:
                color = (0, 200, 0)   # green = recognised
                seen_students.add(student_id)

                # Require CONFIRM_FRAMES consecutive frames before marking
                self._pending_marks[student_id] = \
                    self._pending_marks.get(student_id, 0) + 1

                if self._pending_marks[student_id] >= self.CONFIRM_FRAMES:
                    self.mark_attendance(student_id, label)
            else:
                label = 'Unknown'

            # Draw box + label on original-scale frame
            t, r, b, l = [v * inv_scale for v in loc]
            cv2.rectangle(frame, (l, t), (r, b), color, 2)
            cv2.rectangle(frame, (l, b - 35), (r, b), color, cv2.FILLED)
            cv2.putText(frame, label, (l + 6, b - 6),
                        cv2.FONT_HERSHEY_DUPLEX, 0.75, (255, 255, 255), 1)

            # Confidence % in top-left corner of box
            if conf > 0:
                pct = f'{conf*100:.0f}%'
                cv2.putText(frame, pct, (l + 6, t + 20),
                            cv2.FONT_HERSHEY_DUPLEX, 0.55, (255, 255, 255), 1)

        # Reset pending counts for students NOT seen in this frame
        for sid in list(self._pending_marks.keys()):
            if sid not in seen_students:
                self._pending_marks[sid] = 0

        _, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes()

    def gen_frames(self):
        """Generator for Flask's streaming response."""
        while True:
            frame = self.get_frame()
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    # ── Utility ───────────────────────────────────────────────────────────────
    def encode_image_file(self, img_path: str):
        """Return face encoding from a file path, or None if no face found.
        Uses num_jitters for more robust encodings during registration."""
        image = face_recognition.load_image_file(img_path)

        # Preprocess for consistent lighting
        image = self._preprocess_frame(image)

        encs = face_recognition.face_encodings(
            image, num_jitters=self.NUM_JITTERS
        )
        return encs[0] if encs else None

    def encode_image_file_multi(self, img_path: str):
        """
        Return multiple augmented encodings from a single image for
        better recognition accuracy.  Returns a list of encodings.
        """
        import random as _rand

        image = face_recognition.load_image_file(img_path)
        results = []

        # Original (with preprocessing)
        processed = self._preprocess_frame(image)
        encs = face_recognition.face_encodings(
            processed, num_jitters=self.NUM_JITTERS
        )
        if not encs:
            return []
        results.append(encs[0])

        # Slight brightness variations to improve robustness
        for brightness_shift in [-20, 20]:
            augmented = np.clip(
                image.astype(np.int16) + brightness_shift, 0, 255
            ).astype(np.uint8)
            augmented = self._preprocess_frame(augmented)
            aug_encs = face_recognition.face_encodings(
                augmented, num_jitters=1
            )
            if aug_encs:
                results.append(aug_encs[0])

        # Horizontal flip (helps with left/right angle variance)
        flipped = np.fliplr(image).copy()
        flipped = self._preprocess_frame(flipped)
        flip_encs = face_recognition.face_encodings(
            flipped, num_jitters=1
        )
        if flip_encs:
            results.append(flip_encs[0])

        return results
