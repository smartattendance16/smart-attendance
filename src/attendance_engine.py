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
from datetime import date, datetime

from db import get_db, USE_PG


class AttendanceEngine:
    def __init__(self, encodings_path: str, db_path: str, attendance_dir: str):
        self.encodings_path  = encodings_path
        self.db_path         = db_path
        self.attendance_dir  = attendance_dir

        self.known_data      = self._load_encodings()
        self.video           = None
        self._lock           = threading.Lock()
        self._marked_today   : set = set()

        os.makedirs(attendance_dir, exist_ok=True)

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

    # ── Frame processing ──────────────────────────────────────────────────────
    def get_frame(self) -> bytes | None:
        if not self.video or not self.video.isOpened():
            return None

        ok, frame = self.video.read()
        if not ok:
            return None

        # Downscale for faster recognition
        small     = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb_small)
        encs      = face_recognition.face_encodings(rgb_small, locations)

        for enc, loc in zip(encs, locations):
            label      = 'Unknown'
            student_id = None
            color      = (0, 0, 220)   # red = unknown

            if self.known_data['encodings']:
                matches   = face_recognition.compare_faces(
                    self.known_data['encodings'], enc, tolerance=0.50
                )
                distances = face_recognition.face_distance(
                    self.known_data['encodings'], enc
                )
                best = int(np.argmin(distances))
                if matches[best]:
                    student_id = self.known_data['ids'][best]
                    label      = self.known_data['names'][best]
                    color      = (0, 200, 0)   # green = recognised
                    self.mark_attendance(student_id, label)

            # Draw box + label on original-scale frame
            top, right, bottom, left = [v * 4 for v in loc]
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            cv2.putText(frame, label, (left + 6, bottom - 6),
                        cv2.FONT_HERSHEY_DUPLEX, 0.75, (255, 255, 255), 1)

            # Confidence % in top-left corner of box
            if student_id and self.known_data['encodings']:
                conf = max(0, 1 - distances[best])
                pct  = f'{conf*100:.0f}%'
                cv2.putText(frame, pct, (left + 6, top + 20),
                            cv2.FONT_HERSHEY_DUPLEX, 0.55, (255, 255, 255), 1)

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
        """Return face encoding from a file path, or None if no face found."""
        image = face_recognition.load_image_file(img_path)
        encs  = face_recognition.face_encodings(image)
        return encs[0] if encs else None
