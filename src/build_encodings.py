#!/usr/bin/env python3
"""
build_encodings.py
------------------
Scans the dataset/ folder and rebuilds encodings.pkl from scratch.
Run this whenever you add/remove images manually from dataset/.

Dataset folder structure:
    dataset/
    └── STU001/          ← folder name = student_id
        ├── 1.jpg
        ├── 2.jpg
        ...

Student names are pulled from the SQLite database.

Usage (from project root):
    python src/build_encodings.py

Options:
    --verbose    Print each image being processed
"""

import os
import sys
import pickle
import sqlite3
import argparse
import face_recognition

# ── Paths (relative to this file) ────────────────────────────────────────────
BASE_DIR      = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATASET_DIR   = os.path.join(BASE_DIR, 'dataset')
ENCODINGS_DIR = os.path.join(BASE_DIR, 'encodings')
ENCODINGS_PKL = os.path.join(ENCODINGS_DIR, 'encodings.pkl')
DB_PATH       = os.path.join(BASE_DIR, 'attendance', 'attendance.db')

IMG_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}


def get_name_map() -> dict:
    """Return {student_id: name} from the database."""
    if not os.path.exists(DB_PATH):
        return {}
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute('SELECT student_id, name FROM students').fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}


def build(verbose: bool = False):
    os.makedirs(ENCODINGS_DIR, exist_ok=True)

    name_map = get_name_map()

    encodings_list : list = []
    ids_list       : list = []
    names_list     : list = []

    student_dirs = [d for d in os.listdir(DATASET_DIR)
                    if os.path.isdir(os.path.join(DATASET_DIR, d))]

    if not student_dirs:
        print('[WARNING] No student folders found in dataset/')
        return

    total_images  = 0
    total_encoded = 0

    for sid in sorted(student_dirs):
        name       = name_map.get(sid, sid)   # fallback: use folder name
        folder     = os.path.join(DATASET_DIR, sid)
        images     = [f for f in os.listdir(folder)
                      if os.path.splitext(f)[1].lower() in IMG_EXTS]

        if not images:
            print(f'   [WARNING] {sid} -- no images found, skipping.')
            continue

        print(f'[STUDENT] {name} ({sid}) -- {len(images)} image(s)')

        for img_file in images:
            total_images += 1
            img_path = os.path.join(folder, img_file)

            if verbose:
                print(f'   -> {img_file}', end=' ')

            image = face_recognition.load_image_file(img_path)
            encs  = face_recognition.face_encodings(image)

            if encs:
                encodings_list.append(encs[0])
                ids_list.append(sid)
                names_list.append(name)
                total_encoded += 1
                if verbose:
                    print('[OK]')
            else:
                if verbose:
                    print('[WARNING] no face detected')
                else:
                    print(f'   [WARNING] no face in {img_file}')

    data = {'encodings': encodings_list, 'ids': ids_list, 'names': names_list}

    with open(ENCODINGS_PKL, 'wb') as f:
        pickle.dump(data, f)

    print(f'\n[DONE] {total_encoded}/{total_images} encodings saved -> {ENCODINGS_PKL}')
    print(f'   Students encoded: {len(set(ids_list))}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build face encodings from dataset/')
    parser.add_argument('--verbose', action='store_true',
                        help='Show each image being processed')
    args = parser.parse_args()
    build(verbose=args.verbose)
