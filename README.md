# Smart Attendance System Using Face Recognition

---

## 1. Abstract

The **Smart Attendance System** is a web-based application that automates the process of marking student attendance using real-time face recognition technology. Traditional attendance methods are time-consuming, error-prone, and susceptible to proxy attendance. This system addresses these challenges by leveraging computer vision and deep learning-based facial encoding techniques.

The system captures live video through a webcam, detects faces in the frame, compares them against a pre-built database of student facial encodings, and automatically marks identified students as present. It features a comprehensive admin dashboard for student registration, attendance reporting, data export, and multi-admin management. A student self-registration portal allows students to submit their own registration requests for admin approval. Secure OTP-based password recovery via email ensures robust authentication.

**Keywords**: Face Recognition, Attendance System, Computer Vision, OpenCV, Deep Learning, Flask, Python

---

## 2. Introduction

### 2.1 Background

Attendance tracking is a fundamental requirement in educational institutions. Conventional methods such as manual roll calls, sign-in sheets, and RFID-based systems suffer from several limitations including time consumption, human error, and the potential for proxy attendance. There is a growing need for an automated, contactless, and reliable attendance system.

### 2.2 Problem Statement

To design and develop a web-based smart attendance management system that uses real-time face recognition to automatically identify registered students and record their attendance, eliminating the need for manual intervention.

### 2.3 Objectives

1. Develop a face recognition-based attendance system with real-time webcam processing.
2. Build a web-based admin dashboard for managing students, viewing reports, and exporting data.
3. Implement a student self-registration portal with photo upload and admin approval workflow.
4. Provide secure multi-admin authentication with OTP-based password recovery.
5. Support attendance data export in CSV and Excel formats.
6. Ensure the system is accessible over the network and from mobile devices.

### 2.4 Scope

The system is designed for deployment within educational institutions such as colleges and universities. It supports:
- Real-time face detection and recognition via webcam
- Student registration with multiple face images
- Daily attendance tracking with duplicate prevention
- Date-range and department-filtered reporting
- Multi-admin access with role management
- Public student self-registration with admin approval
- Mobile-responsive web interface
- Public URL access via network tunneling

---

## 3. Literature Survey

| Ref | Title | Key Contribution |
|-----|-------|------------------|
| [1] | Turk, M. & Pentland, A. (1991). "Eigenfaces for Recognition" | Introduced PCA-based face recognition (Eigenfaces), the foundation of modern facial identification systems. |
| [2] | King, D.E. (2009). "Dlib-ml: A Machine Learning Toolkit" | Developed the dlib library with HOG-based face detection and deep metric learning for face encoding. |
| [3] | Schroff, F. et al. (2015). "FaceNet: A Unified Embedding for Face Recognition" | Proposed triplet loss for learning 128-dimensional face embeddings, enabling one-shot recognition. |
| [4] | He, K. et al. (2016). "Deep Residual Learning for Image Recognition" | Introduced ResNet architecture used in modern face recognition models. |
| [5] | Geitgey, A. (2017). "face_recognition: The world's simplest face recognition library" | Built a high-level Python API over dlib for face detection, encoding, and comparison. |

The system builds upon these foundational works, using dlib's deep learning-based face encoding (128-dimensional vectors) with a k-nearest neighbors comparison approach for real-time identification.

---

## 4. System Design

### 4.1 Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Backend Framework | Python 3.10+ / Flask 3.0 | Web server, routing, session management |
| Face Recognition | face_recognition 1.3 (dlib) | Face detection and 128-dim encoding |
| Computer Vision | OpenCV 4.9+ | Webcam capture, frame processing, rendering |
| Database | SQLite3 | Lightweight relational data storage |
| Frontend | HTML5, CSS3, JavaScript | User interface |
| UI Framework | Bootstrap 5.3.2 | Responsive layout, components |
| Authentication | Flask-Login 0.6+ | Session-based admin authentication |
| Password Security | Werkzeug 3.0+ (scrypt) | Secure password hashing |
| Data Export | Pandas 2.2+ / OpenPyXL 3.1+ | CSV and Excel report generation |
| Email Service | smtplib (Gmail SMTP/TLS) | OTP delivery for password recovery |
| Public Access | localtunnel (Node.js) | HTTPS tunnel for remote access |

### 4.2 System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      CLIENT (Browser)                        │
│  ┌─────────┐ ┌──────────┐ ┌────────┐ ┌────────┐ ┌────────┐  │
│  │  Login  │ │Dashboard │ │ Camera │ │Reports │ │Settings│  │
│  └────┬────┘ └────┬─────┘ └───┬────┘ └───┬────┘ └───┬────┘  │
│       └───────────┴────────┬──┴──────────┴──────────┘        │
│                            │ HTTP/HTTPS                      │
├────────────────────────────┼─────────────────────────────────┤
│                      FLASK SERVER                            │
│  ┌─────────────┐  ┌───────┴───────┐  ┌───────────────────┐  │
│  │ Auth Module  │  │ Route Handler │  │ Attendance Engine │  │
│  │ Flask-Login  │  │   (app.py)    │  │(attendance_engine)│  │
│  │ OTP / Email  │  │               │  │  Face Recognition │  │
│  └──────┬──────┘  └───────┬───────┘  │  OpenCV + dlib    │  │
│         │                 │          └────────┬──────────┘  │
├─────────┴─────────────────┴───────────────────┴─────────────┤
│                       DATA LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│  │  SQLite DB   │  │ encodings.pkl│  │  Dataset Images    │ │
│  │  (attendance │  │ (128-dim face│  │  (dataset/STU001/) │ │
│  │   .db)       │  │  vectors)    │  │                    │ │
│  └──────────────┘  └──────────────┘  └────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### 4.3 Data Flow Diagram

**Level 0 — Context Diagram:**
```
                    ┌───────────────┐
   Admin ───────────┤               ├─────── Attendance Reports
                    │  SmartAttend  │
   Student ─────────┤    System     ├─────── Registration Status
                    │               │
   Webcam ──────────┤               ├─────── Attendance Records
                    └───────────────┘
```

**Level 1 — Process Decomposition:**
```
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│  Admin   │────▶│ 1.0 Auth     │────▶│ Admin DB     │
└──────────┘     │   Module     │     └──────────────┘
                 └──────────────┘
                        │
           ┌────────────┼────────────────┐
           ▼            ▼                ▼
   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
   │2.0 Student   │ │3.0 Attendance│ │4.0 Reporting  │
   │ Registration │ │  Processing  │ │  & Export     │
   └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
          ▼                ▼                ▼
   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
   │Students DB + │ │Attendance DB │ │ CSV / Excel   │
   │Encodings.pkl │ │+ Daily CSV   │ │    Files      │
   └──────────────┘ └──────────────┘ └──────────────┘
```

---

## 5. Module Description

### 5.1 Authentication Module
- Admin login with username and password (scrypt-hashed)
- Session management via Flask-Login
- Multi-admin support (add, delete, reset password)
- OTP-based password recovery via Gmail SMTP

### 5.2 Student Registration Module
- **Admin Registration**: Upload 1–5 face photos per student with metadata (ID, name, department, email, phone)
- **Self-Registration Portal**: Public page where students submit their details and a photo for admin review
- **Approval Workflow**: Admin can approve or reject pending registrations
- Face encoding extraction and persistence to `encodings.pkl`

### 5.3 Face Recognition & Attendance Module
- Webcam capture with OpenCV (`cv2.VideoCapture`)
- Frame downscaling (0.25x) for faster processing
- Face detection using HOG (Histogram of Oriented Gradients)
- 128-dimensional face encoding via deep learning (dlib ResNet)
- Comparison against stored encodings with tolerance threshold of 0.50
- Automatic attendance marking (once per student per day)
- Dual storage: SQLite database + daily CSV file
- Real-time visual feedback: green box (recognized), red box (unknown), confidence percentage

### 5.4 Reporting & Export Module
- Date-range filtering (from/to)
- Department-based filtering
- Per-student attendance summary with percentage and progress bar
- Two viewing modes: flat list and grouped by date
- Export to CSV and Excel (XLSX) formats

### 5.5 Settings Module
- Add/remove admin accounts
- Reset admin passwords
- Configure email for each admin (for OTP delivery)

---

## 6. Database Design

### 6.1 Entity-Relationship Diagram

```
┌──────────────┐       ┌──────────────────┐       ┌──────────────┐
│    admin     │       │    attendance     │       │   students   │
├──────────────┤       ├──────────────────┤       ├──────────────┤
│ id (PK)      │       │ id (PK)          │       │ id (PK)      │
│ username (UQ)│       │ student_id (FK)  │◀─────▶│ student_id   │
│ password     │       │ name             │       │   (UQ)       │
│ email        │       │ date             │       │ name         │
└──────────────┘       │ time             │       │ email        │
                       │ status           │       │ department   │
┌──────────────┐       └──────────────────┘       │ phone        │
│  otp_tokens  │                                  │ created_at   │
├──────────────┤       ┌──────────────────┐       └──────────────┘
│ id (PK)      │       │pending_students  │
│ username     │       ├──────────────────┤
│ otp          │       │ id (PK)          │
│ expires_at   │       │ student_id (UQ)  │
│ used         │       │ name, email, ... │
└──────────────┘       │ photo_path       │
                       │ status           │
                       │ submitted_at     │
                       │ reviewed_at      │
                       │ reviewed_by      │
                       └──────────────────┘
```

### 6.2 Table Definitions

| Table | Primary Key | Unique Columns | Purpose |
|-------|-------------|----------------|---------|
| `admin` | id | username | Admin user accounts |
| `students` | id | student_id | Registered student records |
| `attendance` | id | — | Daily attendance entries |
| `pending_students` | id | student_id | Self-registration queue |
| `otp_tokens` | id | — | Password reset OTP tokens |

---

## 7. Implementation

### 7.1 Directory Structure

```
smart_attendance/
├── run.py                          # Application launcher
├── requirements.txt                # Python dependencies
├── src/
│   ├── app.py                      # Flask application (790 lines)
│   ├── attendance_engine.py        # Face recognition engine (183 lines)
│   └── build_encodings.py          # Batch encoding builder (120 lines)
├── templates/                      # 12 HTML templates (Jinja2)
├── static/
│   └── style.css                   # Custom stylesheet
├── dataset/                        # Student face images
├── encodings/                      # Serialized face encodings
├── attendance/                     # SQLite DB + daily CSVs
└── pending_photos/                 # Self-registration uploads
```

### 7.2 Face Recognition Algorithm

```
Algorithm: Real-Time Face Attendance

Input:  Webcam frame, Known encodings database
Output: Annotated frame, Attendance record

1. Capture frame from webcam
2. Resize frame to 25% (for speed)
3. Convert BGR → RGB color space
4. Detect all face locations using HOG detector
5. For each detected face:
   a. Compute 128-dimensional encoding vector
   b. Compare against all known encodings
   c. Calculate Euclidean distances
   d. If minimum distance ≤ 0.50 (tolerance):
      - Identify student (name, ID)
      - Mark attendance in database (if not already marked today)
      - Append to daily CSV
      - Draw GREEN bounding box with name and confidence
   e. Else:
      - Draw RED bounding box with "Unknown"
6. Encode frame as JPEG
7. Yield frame to MJPEG stream
8. Repeat from step 1
```

### 7.3 Key Implementation Details

- **MJPEG Streaming**: The camera feed uses Flask's streaming response with `multipart/x-mixed-replace` boundary for real-time video delivery to the browser without WebSocket overhead.
- **Thread Safety**: Attendance marking uses a `threading.Lock` to prevent race conditions in concurrent database writes.
- **Duplicate Prevention**: Two-layer check — in-memory `set` for session-level and SQL query for persistent check — ensures each student is marked only once per day.
- **Encoding Persistence**: Face encodings are serialized using Python's `pickle` module for fast load/save operations.

---

## 8. Screenshots

### 8.1 Login Page
- Clean gradient background with branded card layout
- Secure login form with username/password fields
- "Forgot Password?" link for OTP-based recovery
- "Student? Register here" link for self-registration

### 8.2 Dashboard
- Real-time statistics: Total Students, Present Today, Absent Today
- Quick action buttons: Start Camera, Register Student, Export Today
- Recent activity table showing latest attendance records

### 8.3 Live Camera
- Start/Stop camera controls with live status indicator
- Real-time video feed with face detection overlays
- Green boxes for recognized students, red for unknown
- Confidence percentage displayed per face

### 8.4 Reports
- Date range and department filters
- Student summary table with attendance percentage and progress bars
- Flat list and grouped-by-date viewing modes
- One-click CSV and Excel export

### 8.5 Student Self-Registration
- Public-facing registration form (no login required)
- Photo upload with live preview
- Admin receives the request in the Approvals queue

---

## 9. Testing

### 9.1 Test Results

| # | Test Case | Input | Expected Result | Actual Result | Status |
|---|-----------|-------|-----------------|---------------|--------|
| 1 | Invalid login | Wrong password | Error flash message | Error shown, stays on login | ✅ Pass |
| 2 | Valid login | admin / admin123 | Redirect to dashboard | Redirected to /dashboard | ✅ Pass |
| 3 | Dashboard load | Authenticated session | Stats + recent table | Loaded with correct data | ✅ Pass |
| 4 | Report page | Date range filter | Filtered records | Correct records shown | ✅ Pass |
| 5 | Register page | Authenticated session | Form + student list | Both rendered correctly | ✅ Pass |
| 6 | Settings page | Authenticated session | Admin list + add form | All admins listed | ✅ Pass |
| 7 | Approvals page | Authenticated session | Pending queue | Queue rendered | ✅ Pass |
| 8 | Camera page | Authenticated session | Video controls | Start/Stop buttons work | ✅ Pass |
| 9 | CSV export | Date range | CSV download | File downloaded, text/csv | ✅ Pass |
| 10 | Excel export | Date range | XLSX download | File downloaded, correct MIME | ✅ Pass |
| 11 | Self-register (public) | No auth | Registration form | Form accessible | ✅ Pass |
| 12 | Forgot password | Valid username | OTP generated + emailed | OTP sent to email | ✅ Pass |
| 13 | OTP verification | Correct OTP | Redirect to reset page | Password reset successful | ✅ Pass |
| 14 | Logout | Authenticated session | Session cleared | Redirected to login | ✅ Pass |
| 15 | Auth guard | Unauthenticated access | Redirect to login | Redirected to /login | ✅ Pass |
| 16 | OTP email delivery | Gmail SMTP | Email in inbox | Email received successfully | ✅ Pass |

### 9.2 Performance Observations

| Metric | Value |
|--------|-------|
| Face detection speed (per frame) | ~50–100ms |
| Face encoding computation | ~80–150ms |
| Recognition accuracy (well-lit conditions) | ~95%+ |
| Maximum concurrent recognized faces | 5–8 per frame |
| Attendance marking latency | < 10ms |

---

## 10. Advantages and Limitations

### 10.1 Advantages
1. **Automated and contactless** — No manual roll call or physical contact needed
2. **Proxy-resistant** — Face recognition prevents impersonation
3. **Real-time processing** — Instant attendance marking as students face the camera
4. **Comprehensive reporting** — Detailed analytics with export capabilities
5. **Mobile responsive** — Accessible from phones and tablets
6. **Self-registration** — Reduces admin workload with approval workflow
7. **Secure authentication** — Hashed passwords and OTP-based recovery
8. **Lightweight** — SQLite requires no database server setup
9. **Remotely accessible** — Public URL via tunneling for network access

### 10.2 Limitations
1. Accuracy degrades in poor lighting conditions
2. Identical twins may cause false matches
3. Camera must be connected to the server machine
4. SQLite may face concurrency limitations at very large scale
5. Face masks or significant appearance changes may reduce recognition accuracy
6. Requires initial enrollment of clear face photos for each student

---

## 11. Conclusion

The Smart Attendance System successfully demonstrates the practical application of face recognition technology in automating attendance management. The system achieves reliable real-time identification of registered students through a webcam feed, significantly reducing the time and effort required for traditional attendance methods.

The web-based interface provides administrators with comprehensive tools for student management, attendance tracking, and data analysis. The self-registration portal and approval workflow streamline the enrollment process. Security features including hashed passwords, OTP-based recovery, and session management ensure robust access control.

The system is suitable for deployment in college classrooms, laboratories, and seminar halls. With minor enhancements such as liveness detection and cloud database migration, it can be scaled for institution-wide deployment.

---

## 12. Future Enhancements

1. **Anti-spoofing / Liveness Detection** — Prevent photo-based attacks using blink detection or depth analysis
2. **Multiple Camera Support** — Simultaneous feeds from multiple classrooms
3. **Push Notifications** — Email or SMS alerts to students/parents upon attendance marking
4. **Role-Based Access Control** — Differentiate between teacher, HOD, and super admin roles
5. **Late/Half-Day Rules** — Configurable time thresholds for late marking
6. **Student Portal** — Allow students to view their own attendance history
7. **Cloud Database Migration** — PostgreSQL or MySQL for production scalability
8. **Docker Containerization** — Simplified deployment across environments
9. **Analytics Dashboard** — Visual charts and trend analysis
10. **Bulk Student Import** — CSV-based batch registration

---

## 13. References

1. Turk, M. and Pentland, A., 1991. "Eigenfaces for recognition." *Journal of Cognitive Neuroscience*, 3(1), pp.71–86.
2. King, D.E., 2009. "Dlib-ml: A machine learning toolkit." *Journal of Machine Learning Research*, 10, pp.1755–1758.
3. Schroff, F., Kalenichenko, D., and Philbin, J., 2015. "FaceNet: A unified embedding for face recognition and clustering." *IEEE Conference on Computer Vision and Pattern Recognition (CVPR)*.
4. He, K., Zhang, X., Ren, S., and Sun, J., 2016. "Deep residual learning for image recognition." *IEEE Conference on Computer Vision and Pattern Recognition (CVPR)*.
5. Flask Web Framework. https://flask.palletsprojects.com/
6. OpenCV Library. https://opencv.org/
7. Python face_recognition Library. https://github.com/ageitgey/face_recognition
8. Bootstrap 5 Framework. https://getbootstrap.com/

---

## Appendix A: Installation Guide

### Prerequisites
- Python 3.10 or above
- Node.js (optional, for public URL)
- Webcam (for live attendance)
- CMake and Visual Studio Build Tools (for dlib on Windows)

### Installation Steps

```bash
# Step 1: Navigate to project directory
cd smart_attendance

# Step 2: Install Python dependencies
pip install -r requirements.txt

# Step 3: Run the application
python src/app.py

# Step 4: Access in browser
# Open http://localhost:5000

# Step 5 (Optional): Public URL
python run.py --tunnel --name smartattend16
# Access at: https://smartattend16.loca.lt
```

### Dependencies (requirements.txt)
```
flask>=3.0
flask-login>=0.6
opencv-python>=4.9
face-recognition>=1.3
numpy>=1.26
pandas>=2.2
openpyxl>=3.1
werkzeug>=3.0
```

---

## Appendix B: API Routes

### Public Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET/POST | `/login` | Admin login |
| GET/POST | `/self-register` | Student self-registration |
| GET/POST | `/forgot-password` | OTP request |
| GET/POST | `/verify-otp` | OTP verification |
| GET/POST | `/reset-password` | Password reset |

### Protected Endpoints (Admin Only)

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/dashboard` | Dashboard with statistics |
| GET | `/camera` | Live camera page |
| GET | `/camera/start` | Open webcam |
| GET | `/camera/stop` | Close webcam |
| GET | `/video_feed` | MJPEG video stream |
| GET/POST | `/register` | Student registration |
| GET | `/report` | Attendance reports |
| GET | `/export` | CSV/Excel download |
| GET | `/approvals` | Approval queue |
| GET | `/settings` | Admin management |
| GET | `/logout` | End session |
