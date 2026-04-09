"""
app.py  —  Smart Attendance System
Run from project root:  python src/app.py
"""

import os
import io
import random
import string
import smtplib
import logging
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date, datetime, timedelta

import pandas as pd
from flask import (Flask, Response, flash, redirect, render_template,
                   request, send_file, url_for, session, jsonify)
from flask_login import (LoginManager, UserMixin, current_user, login_required,
                         login_user, logout_user)
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_db as _raw_get_db, init_db as _raw_init_db, DBIntegrityError, USE_PG
from attendance_engine import AttendanceEngine, DETECTION_MODEL

import cv2
import numpy as np
import face_recognition

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('smartattend')

# ── Paths ─────────────────────────────────────────────────────────────────────
SRC_DIR       = os.path.dirname(os.path.abspath(__file__))
BASE_DIR      = os.path.abspath(os.path.join(SRC_DIR, '..'))
TEMPLATE_DIR  = os.path.join(BASE_DIR, 'templates')
STATIC_DIR    = os.path.join(BASE_DIR, 'static')
DATASET_DIR   = os.path.join(BASE_DIR, 'dataset')
ENCODINGS_DIR = os.path.join(BASE_DIR, 'encodings')
ATTENDANCE_DIR= os.path.join(BASE_DIR, 'attendance')
ENCODINGS_PKL = os.path.join(ENCODINGS_DIR, 'encodings.pkl')
DB_PATH       = os.path.join(ATTENDANCE_DIR, 'attendance.db')

os.makedirs(DATASET_DIR,    exist_ok=True)
os.makedirs(ENCODINGS_DIR,  exist_ok=True)
os.makedirs(ATTENDANCE_DIR, exist_ok=True)

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(32).hex())

# CSRF Protection
csrf = CSRFProtect(app)

# Rate Limiting
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri='memory://',
)

# Trust reverse proxy headers (Render) so url_for(_external=True) works correctly
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ── Template filters ──────────────────────────────────────────────────────────
@app.template_filter('fmtdate')
def fmtdate(value):
    """Format a date/datetime/string to YYYY-MM-DD."""
    if value is None:
        return '—'
    if isinstance(value, str):
        return value[:10]
    try:
        return value.strftime('%Y-%m-%d')
    except Exception:
        return str(value)[:10]

@app.template_filter('fmtdatetime')
def fmtdatetime(value):
    """Format to YYYY-MM-DD HH:MM."""
    if value is None:
        return '—'
    if isinstance(value, str):
        return value[:16]
    try:
        return value.strftime('%Y-%m-%d %H:%M')
    except Exception:
        return str(value)[:16]

# ── Database helpers ──────────────────────────────────────────────────────────
def get_db():
    return _raw_get_db(DB_PATH)

def init_db():
    _raw_init_db(DB_PATH)

# ── Audit Log Helper ──────────────────────────────────────────────────────────
def log_action(action, target='', details=''):
    """Record an admin action in the audit log."""
    user = current_user.username if current_user.is_authenticated else 'system'
    try:
        conn = get_db()
        conn.execute(
            'INSERT INTO audit_log (admin_user, action, target, details) VALUES (?,?,?,?)',
            (user, action, target, details)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass  # Don't let audit logging break the main flow

# ── Attendance Engine (singleton) ─────────────────────────────────────────────
engine = AttendanceEngine(ENCODINGS_PKL, DB_PATH, ATTENDANCE_DIR)

# ── Auth ──────────────────────────────────────────────────────────────────────
class Admin(UserMixin):
    def __init__(self, id, username):
        self.id       = id
        self.username = username

@login_manager.user_loader
def load_user(uid):
    conn  = get_db()
    row   = conn.execute('SELECT * FROM admin WHERE id=?', (uid,)).fetchone()
    conn.close()
    return Admin(row['id'], row['username']) if row else None

# ── OTP Helpers ───────────────────────────────────────────────────────────────
EMAIL_CONFIG = {
    'smtp_server': os.environ.get('SMTP_SERVER', 'smtp.gmail.com'),
    'smtp_port'  : int(os.environ.get('SMTP_PORT', 587)),
    'sender'     : os.environ.get('SMTP_EMAIL', 'smartattendance16@gmail.com'),
    'password'   : os.environ.get('SMTP_PASSWORD', ''),
}

def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))

def save_otp(username, otp):
    expires = datetime.now() + timedelta(minutes=10)
    conn    = get_db()
    conn.execute('UPDATE otp_tokens SET used=1 WHERE username=?', (username,))
    conn.execute(
        'INSERT INTO otp_tokens (username, otp, expires_at) VALUES (?,?,?)',
        (username, otp, expires)
    )
    conn.commit()
    conn.close()

def verify_otp(username, otp):
    conn  = get_db()
    token = conn.execute(
        'SELECT * FROM otp_tokens WHERE username=? AND otp=? AND used=0 ORDER BY id DESC LIMIT 1',
        (username, otp)
    ).fetchone()
    if not token:
        conn.close()
        return False, 'Invalid OTP.'
    if datetime.now() > datetime.fromisoformat(str(token['expires_at'])):
        conn.close()
        return False, 'OTP has expired. Please request a new one.'
    conn.execute('UPDATE otp_tokens SET used=1 WHERE id=?', (token['id'],))
    conn.commit()
    conn.close()
    return True, 'OK'

def _send_otp_email_sync(to_email, username, otp):
    """Actual SMTP send (runs in background thread)."""
    try:
        msg            = MIMEMultipart('alternative')
        msg['Subject'] = 'SmartAttend — Password Reset OTP'
        msg['From']    = EMAIL_CONFIG['sender']
        msg['To']      = to_email
        html = f"""
        <div style="font-family:sans-serif;max-width:480px;margin:auto">
          <div style="background:#4f46e5;padding:1.5rem;border-radius:12px 12px 0 0;text-align:center">
            <h2 style="color:#fff;margin:0">🎓 SmartAttend</h2>
          </div>
          <div style="background:#fff;padding:2rem;border:1px solid #e2e8f0;border-radius:0 0 12px 12px">
            <p>Hello <strong>{username}</strong>,</p>
            <p>Your password reset OTP is:</p>
            <div style="background:#f1f5f9;border-radius:10px;padding:1.5rem;text-align:center;
                        font-size:2.5rem;font-weight:700;letter-spacing:.5rem;color:#4f46e5">
              {otp}
            </div>
            <p style="color:#64748b;font-size:.85rem;margin-top:1rem">
              This OTP is valid for <strong>10 minutes</strong>. Do not share it with anyone.
            </p>
          </div>
        </div>"""
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'], timeout=10) as s:
            s.starttls()
            s.login(EMAIL_CONFIG['sender'], EMAIL_CONFIG['password'])
            s.sendmail(EMAIL_CONFIG['sender'], to_email, msg.as_string())
        logger.info(f'OTP email sent to {to_email}')
    except Exception as e:
        logger.error(f'OTP email to {to_email} failed: {e}')

def send_otp_email_async(to_email, username, otp):
    """Fire-and-forget: sends OTP email in a background thread."""
    if not EMAIL_CONFIG['sender'] or not EMAIL_CONFIG['password']:
        return
    t = threading.Thread(target=_send_otp_email_sync, args=(to_email, username, otp), daemon=True)
    t.start()

# ── Routes: Auth ──────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return redirect(url_for('dashboard') if current_user.is_authenticated else url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit('10 per minute')
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn     = get_db()
        row      = conn.execute('SELECT * FROM admin WHERE username=?', (username,)).fetchone()
        conn.close()
        if row and check_password_hash(row['password'], password):
            login_user(Admin(row['id'], row['username']))
            log_action('login', username, 'Successful login')
            return redirect(url_for('dashboard'))
        logger.warning(f'Failed login attempt for username: {username}')
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    engine.close_camera()
    logout_user()
    return redirect(url_for('login'))

# ── Forgot Password — Step 1 ─────────────────────────────────────────────────
@app.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit('5 per minute')
def forgot_password():
    if request.method == 'POST':
        username = request.form['username'].strip()
        conn     = get_db()
        admin    = conn.execute('SELECT * FROM admin WHERE username=?', (username,)).fetchone()
        conn.close()

        if not admin:
            flash('No admin account found with that username.', 'danger')
            return redirect(url_for('forgot_password'))

        otp = generate_otp()
        save_otp(username, otp)

        print(f'\n{"="*45}')
        print(f'  [OTP] PASSWORD RESET OTP for "{username}"')
        print(f'  OTP: {otp}')
        print(f'  Valid for 10 minutes')
        print(f'{"="*45}\n')

        if admin['email']:
            send_otp_email_async(admin['email'], username, otp)
            flash(f'OTP sent to {admin["email"][:3]}***. Check your email.', 'success')
        else:
            flash('OTP generated! Check the terminal window where the app is running.', 'info')

        session['otp_username'] = username
        return redirect(url_for('verify_otp_route'))

    return render_template('forgot_password.html')

# ── Forgot Password — Step 2 ─────────────────────────────────────────────────
@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp_route():
    username = session.get('otp_username')
    if not username:
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        otp     = request.form['otp'].strip()
        ok, msg = verify_otp(username, otp)
        if ok:
            session['otp_verified'] = True
            return redirect(url_for('reset_password_route'))
        flash(msg, 'danger')

    return render_template('verify_otp.html', username=username)

# ── Forgot Password — Step 3 ─────────────────────────────────────────────────
@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password_route():
    username = session.get('otp_username')
    verified = session.get('otp_verified')

    if not username or not verified:
        flash('Please complete OTP verification first.', 'danger')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_pw  = request.form['new_password'].strip()
        confirm = request.form['confirm_password'].strip()

        if len(new_pw) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return redirect(request.url)
        if new_pw != confirm:
            flash('Passwords do not match.', 'danger')
            return redirect(request.url)

        conn = get_db()
        conn.execute('UPDATE admin SET password=? WHERE username=?',
                     (generate_password_hash(new_pw), username))
        conn.commit()
        conn.close()

        session.pop('otp_username', None)
        session.pop('otp_verified', None)

        flash('✅ Password reset successfully! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html', username=username)

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    cur, new = request.form['current_password'], request.form['new_password']
    conn = get_db()
    row  = conn.execute('SELECT * FROM admin WHERE id=?', (current_user.id,)).fetchone()
    if row and check_password_hash(row['password'], cur):
        conn.execute('UPDATE admin SET password=? WHERE id=?',
                     (generate_password_hash(new), current_user.id))
        conn.commit()
        flash('Password updated.', 'success')
    else:
        flash('Current password is incorrect.', 'danger')
    conn.close()
    return redirect(url_for('dashboard'))

# ── Routes: Dashboard ─────────────────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    today = date.today().isoformat()
    conn  = get_db()
    total_students   = conn.execute('SELECT COUNT(*) FROM students').fetchone()[0]
    today_present    = conn.execute(
        'SELECT COUNT(DISTINCT student_id) FROM attendance WHERE date=?', (today,)
    ).fetchone()[0]
    recent           = conn.execute('''
        SELECT a.*, s.department FROM attendance a
        LEFT JOIN students s ON a.student_id = s.student_id
        ORDER BY a.date DESC, a.time DESC LIMIT 12
    ''').fetchall()
    departments      = conn.execute(
        "SELECT department, COUNT(*) as cnt FROM students WHERE department != '' GROUP BY department"
    ).fetchall()

    # ── Chart data: last 7 days attendance trend ──
    week_data = []
    for i in range(6, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        cnt = conn.execute(
            'SELECT COUNT(DISTINCT student_id) FROM attendance WHERE date=?', (d,)
        ).fetchone()[0]
        week_data.append({'date': d, 'count': cnt})

    # ── Chart data: department-wise student count ──
    dept_data = []
    for d in departments:
        dept_data.append({'department': d['department'] or 'Unknown', 'count': d['cnt']})

    # ── Top students by attendance this month ──
    month_start = date.today().replace(day=1).isoformat()
    top_students = conn.execute('''
        SELECT a.student_id, a.name, COUNT(DISTINCT a.date) as days
        FROM attendance a
        WHERE a.date >= ?
        GROUP BY a.student_id, a.name
        ORDER BY days DESC LIMIT 5
    ''', (month_start,)).fetchall()

    conn.close()
    return render_template('dashboard.html',
                           total_students=total_students,
                           today_present=today_present,
                           today_absent=total_students - today_present,
                           recent=recent,
                           departments=departments,
                           today=today,
                           week_data=week_data,
                           dept_data=dept_data,
                           top_students=top_students)

# ── Routes: Register ──────────────────────────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    if request.method == 'POST':
        student_id = request.form['student_id'].strip()
        name       = request.form['name'].strip()
        email      = request.form.get('email', '').strip()
        department = request.form.get('department', '').strip()
        phone      = request.form.get('phone', '').strip()

        files = request.files.getlist('face_images')
        if not files or all(f.filename == '' for f in files):
            flash('Please upload at least one face photo.', 'danger')
            return redirect(request.url)

        # Save images to dataset/student_id/
        student_dir = os.path.join(DATASET_DIR, student_id)
        os.makedirs(student_dir, exist_ok=True)

        saved, encoded = 0, 0
        for idx, f in enumerate(files):
            if f.filename == '':
                continue
            ext      = os.path.splitext(f.filename)[1].lower() or '.jpg'
            img_path = os.path.join(student_dir, f'{idx+1}{ext}')
            f.save(img_path)
            saved += 1

            # Generate multiple augmented encodings per image for better accuracy
            multi_encs = engine.encode_image_file_multi(img_path)
            if multi_encs:
                for enc in multi_encs:
                    engine.add_encoding(student_id, name, enc)
                encoded += 1
                logger.info(f'[REGISTER] {student_id}: {len(multi_encs)} encodings from image {idx+1}')
            else:
                os.remove(img_path)

        if encoded == 0:
            flash('No face detected in any of the uploaded photos. Try clearer images.', 'danger')
            return redirect(request.url)

        # Save to DB
        try:
            conn = get_db()
            conn.execute(
                'INSERT INTO students (student_id,name,email,department,phone) VALUES (?,?,?,?,?)',
                (student_id, name, email, department, phone)
            )
            conn.commit()
            conn.close()
        except DBIntegrityError:
            flash(f'Student ID "{student_id}" already exists.', 'danger')
            return redirect(request.url)

        flash(f'✅ {name} registered with {encoded}/{saved} usable photo(s).', 'success')
        log_action('register_student', student_id, f'Registered {name} with {encoded} photos')
        return redirect(url_for('register'))

    # GET — show existing students
    conn = get_db()
    students = conn.execute('SELECT * FROM students ORDER BY name').fetchall()
    conn.close()
    return render_template('register.html', students=students)

@app.route('/students/delete/<student_id>', methods=['POST'])
@login_required
def delete_student(student_id):
    engine.remove_encoding(student_id)

    conn = get_db()
    conn.execute('DELETE FROM students  WHERE student_id=?', (student_id,))
    conn.execute('DELETE FROM attendance WHERE student_id=?', (student_id,))
    conn.commit()
    conn.close()

    # Remove dataset images
    student_dir = os.path.join(DATASET_DIR, student_id)
    if os.path.isdir(student_dir):
        import shutil
        shutil.rmtree(student_dir)

    logger.info(f'Student {student_id} deleted by {current_user.username}')
    log_action('delete_student', student_id, f'Deleted student')
    flash('Student removed.', 'success')
    return redirect(url_for('register'))

@app.route('/students/edit/<student_id>', methods=['GET', 'POST'])
@login_required
def edit_student(student_id):
    conn = get_db()
    student = conn.execute('SELECT * FROM students WHERE student_id=?', (student_id,)).fetchone()
    if not student:
        conn.close()
        flash('Student not found.', 'danger')
        return redirect(url_for('register'))

    if request.method == 'POST':
        name       = request.form['name'].strip()
        email      = request.form.get('email', '').strip()
        department = request.form.get('department', '').strip()
        phone      = request.form.get('phone', '').strip()

        conn.execute(
            'UPDATE students SET name=?, email=?, department=?, phone=? WHERE student_id=?',
            (name, email, department, phone, student_id)
        )
        conn.commit()
        conn.close()

        # Update name in face encodings too
        try:
            conn2 = get_db()
            conn2.execute('UPDATE face_encodings SET name=? WHERE student_id=?', (name, student_id))
            conn2.commit()
            conn2.close()
            engine.reload_encodings()
        except Exception:
            pass

        logger.info(f'Student {student_id} edited by {current_user.username}')
        flash(f'✅ {name} updated successfully.', 'success')
        return redirect(url_for('register'))

    conn.close()
    return render_template('edit_student.html', student=student)

# ── Routes: Camera ────────────────────────────────────────────────────────────
@app.route('/camera')
@login_required
def camera():
    return render_template('camera.html')

@app.route('/camera/start')
@login_required
@csrf.exempt
def camera_start():
    engine.open_camera(0)
    return ('', 204)

@app.route('/camera/stop')
@login_required
@csrf.exempt
def camera_stop():
    engine.close_camera()
    return ('', 204)

@app.route('/video_feed')
@login_required
@csrf.exempt
def video_feed():
    return Response(engine.gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# ── Routes: Report ────────────────────────────────────────────────────────────
@app.route('/report')
@login_required
def report():
    date_from   = request.args.get('date_from', date.today().isoformat())
    date_to     = request.args.get('date_to',   date.today().isoformat())
    dept_filter = request.args.get('department', '')

    conn = get_db()

    departments = conn.execute(
        "SELECT DISTINCT department FROM students WHERE department != '' ORDER BY department"
    ).fetchall()

    query = '''
        SELECT a.student_id, a.name, s.department, a.date, a.time, a.status
        FROM attendance a
        LEFT JOIN students s ON a.student_id = s.student_id
        WHERE a.date BETWEEN ? AND ?
    '''
    params = [date_from, date_to]
    if dept_filter:
        query  += ' AND s.department = ?'
        params.append(dept_filter)
    query += ' ORDER BY a.date DESC, a.time DESC'

    records = conn.execute(query, params).fetchall()

    summary_query = '''
        SELECT a.student_id, a.name, s.department,
               COUNT(DISTINCT a.date) as present_days
        FROM attendance a
        LEFT JOIN students s ON a.student_id = s.student_id
        WHERE a.date BETWEEN ? AND ?
    '''
    s_params = [date_from, date_to]
    if dept_filter:
        summary_query += ' AND s.department = ?'
        s_params.append(dept_filter)
    summary_query += ' GROUP BY a.student_id, a.name, s.department ORDER BY a.name'
    summary = conn.execute(summary_query, s_params).fetchall()

    working_days = conn.execute(
        'SELECT COUNT(DISTINCT date) FROM attendance WHERE date BETWEEN ? AND ?',
        [date_from, date_to]
    ).fetchone()[0]

    conn.close()

    return render_template('report.html',
                           records=records,
                           summary=summary,
                           departments=departments,
                           date_from=date_from,
                           date_to=date_to,
                           dept_filter=dept_filter,
                           working_days=working_days)

# ── Routes: Export ────────────────────────────────────────────────────────────
@app.route('/export')
@login_required
def export():
    date_from = request.args.get('date_from', date.today().isoformat())
    date_to   = request.args.get('date_to',   date.today().isoformat())
    fmt       = request.args.get('format', 'csv')

    conn = get_db()
    rows = conn.execute('''
        SELECT a.student_id, a.name, s.department, a.date, a.time, a.status
        FROM attendance a
        LEFT JOIN students s ON a.student_id = s.student_id
        WHERE a.date BETWEEN ? AND ?
        ORDER BY a.date, a.time
    ''', [date_from, date_to]).fetchall()
    conn.close()

    df = pd.DataFrame(rows, columns=['Student ID', 'Name', 'Department',
                                     'Date', 'Time', 'Status'])
    fname = f'attendance_{date_from}_to_{date_to}'

    if fmt == 'excel':
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as w:
            df.to_excel(w, index=False, sheet_name='Attendance')
        buf.seek(0)
        return send_file(buf,
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True, download_name=f'{fname}.xlsx')

    buf = io.BytesIO(df.to_csv(index=False).encode())
    return send_file(buf, mimetype='text/csv',
                     as_attachment=True, download_name=f'{fname}.csv')

# ── Routes: Student Self-Registration (public) ────────────────────────────────
PENDING_DIR = os.path.join(BASE_DIR, 'pending_photos')
os.makedirs(PENDING_DIR, exist_ok=True)

@app.route('/self-register', methods=['GET', 'POST'])
def self_register():
    if request.method == 'POST':
        student_id = request.form['student_id'].strip()
        name       = request.form['name'].strip()
        email      = request.form.get('email', '').strip()
        department = request.form.get('department', '').strip()
        phone      = request.form.get('phone', '').strip()

        if 'face_image' not in request.files or request.files['face_image'].filename == '':
            flash('Please upload a face photo.', 'danger')
            return redirect(request.url)

        conn = get_db()
        if conn.execute('SELECT 1 FROM students WHERE student_id=?', (student_id,)).fetchone():
            conn.close()
            flash('This Student ID is already registered.', 'danger')
            return redirect(request.url)
        if conn.execute(
            "SELECT 1 FROM pending_students WHERE student_id=? AND status=?",
            (student_id, 'pending')
        ).fetchone():
            conn.close()
            flash('A request for this Student ID is already pending approval.', 'warning')
            return redirect(request.url)
        conn.close()

        file       = request.files['face_image']
        ext        = os.path.splitext(file.filename)[1].lower() or '.jpg'
        filename   = f'{student_id}{ext}'
        photo_path = os.path.join(PENDING_DIR, filename)
        file.save(photo_path)

        enc = engine.encode_image_file(photo_path)
        if enc is None:
            os.remove(photo_path)
            flash('No face detected. Please upload a clear, front-facing photo.', 'danger')
            return redirect(request.url)

        conn = get_db()
        try:
            conn.execute(
                'INSERT INTO pending_students (student_id,name,email,department,phone,photo_path) VALUES (?,?,?,?,?,?)',
                (student_id, name, email, department, phone, photo_path)
            )
            conn.commit()
            flash('Registration submitted! Please wait for admin approval.', 'success')
        except DBIntegrityError:
            flash('A request for this Student ID already exists.', 'warning')
        finally:
            conn.close()
        return redirect(url_for('self_register'))

    return render_template('self_register.html')


@app.route('/approvals')
@login_required
def approvals():
    conn    = get_db()
    pending = conn.execute(
        "SELECT * FROM pending_students WHERE status=? ORDER BY submitted_at DESC",
        ('pending',)
    ).fetchall()
    history = conn.execute(
        "SELECT * FROM pending_students WHERE status != ? ORDER BY reviewed_at DESC LIMIT 30",
        ('pending',)
    ).fetchall()
    conn.close()
    return render_template('approvals.html', pending=pending, history=history)


@app.route('/approvals/approve/<int:req_id>', methods=['POST'])
@login_required
def approve_student(req_id):
    conn = get_db()
    req  = conn.execute('SELECT * FROM pending_students WHERE id=?', (req_id,)).fetchone()
    if not req:
        flash('Request not found.', 'danger')
        conn.close()
        return redirect(url_for('approvals'))

    try:
        conn.execute(
            'INSERT INTO students (student_id,name,email,department,phone) VALUES (?,?,?,?,?)',
            (req['student_id'], req['name'], req['email'], req['department'], req['phone'])
        )
    except DBIntegrityError:
        flash('Student ID already exists.', 'danger')
        if USE_PG:
            conn.rollback()
        conn.execute(
            "UPDATE pending_students SET status=?,reviewed_at=?,reviewed_by=? WHERE id=?",
            ('rejected', datetime.now(), current_user.username, req_id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('approvals'))

    student_dir = os.path.join(DATASET_DIR, req['student_id'])
    os.makedirs(student_dir, exist_ok=True)
    ext      = os.path.splitext(req['photo_path'])[1] or '.jpg'
    new_path = os.path.join(student_dir, f'1{ext}')
    if os.path.exists(req['photo_path']):
        import shutil
        shutil.move(req['photo_path'], new_path)

    enc = engine.encode_image_file(new_path)
    if enc is not None:
        engine.add_encoding(req['student_id'], req['name'], enc)

    conn.execute(
        "UPDATE pending_students SET status=?,reviewed_at=?,reviewed_by=? WHERE id=?",
        ('approved', datetime.now(), current_user.username, req_id)
    )
    conn.commit()
    conn.close()
    logger.info(f'Student {req["name"]} approved by {current_user.username}')
    flash(f'{req["name"]} approved and registered!', 'success')
    return redirect(url_for('approvals'))


@app.route('/approvals/reject/<int:req_id>', methods=['POST'])
@login_required
def reject_student(req_id):
    conn = get_db()
    req  = conn.execute('SELECT * FROM pending_students WHERE id=?', (req_id,)).fetchone()
    if req and req['photo_path'] and os.path.exists(req['photo_path']):
        os.remove(req['photo_path'])
    conn.execute(
        "UPDATE pending_students SET status=?,reviewed_at=?,reviewed_by=? WHERE id=?",
        ('rejected', datetime.now(), current_user.username, req_id)
    )
    conn.commit()
    conn.close()
    logger.info(f'Student request {req_id} rejected by {current_user.username}')
    flash('Request rejected.', 'warning')
    return redirect(url_for('approvals'))


@app.route('/settings')
@login_required
def settings():
    conn   = get_db()
    admins = conn.execute('SELECT id, username, email FROM admin ORDER BY id').fetchall()
    conn.close()
    return render_template('settings.html', admins=admins)

@app.route('/settings/add_admin', methods=['POST'])
@login_required
def add_admin():
    username = request.form['username'].strip()
    password = request.form['password'].strip()
    confirm  = request.form['confirm_password'].strip()
    email    = request.form.get('email', '').strip()

    if not username or not password:
        flash('Username and password are required.', 'danger')
        return redirect(url_for('settings'))

    if password != confirm:
        flash('Passwords do not match.', 'danger')
        return redirect(url_for('settings'))

    if len(password) < 6:
        flash('Password must be at least 6 characters.', 'danger')
        return redirect(url_for('settings'))

    try:
        conn = get_db()
        conn.execute('INSERT INTO admin (username, password, email) VALUES (?,?,?)',
                     (username, generate_password_hash(password), email))
        conn.commit()
        conn.close()
        flash(f'✅ Admin "{username}" added successfully!', 'success')
        log_action('add_admin', username, f'New admin account created')
    except DBIntegrityError:
        flash(f'Username "{username}" already exists.', 'danger')

    return redirect(url_for('settings'))

@app.route('/settings/delete_admin/<int:admin_id>', methods=['POST'])
@login_required
def delete_admin(admin_id):
    if admin_id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('settings'))

    conn   = get_db()
    total  = conn.execute('SELECT COUNT(*) FROM admin').fetchone()[0]
    if total <= 1:
        flash('Cannot delete the last admin account.', 'danger')
        conn.close()
        return redirect(url_for('settings'))

    conn.execute('DELETE FROM admin WHERE id=?', (admin_id,))
    conn.commit()
    conn.close()
    logger.info(f'Admin {admin_id} deleted by {current_user.username}')
    flash('Admin removed.', 'success')
    return redirect(url_for('settings'))

@app.route('/settings/reset_password/<int:admin_id>', methods=['POST'])
@login_required
def reset_admin_password(admin_id):
    new_pw  = request.form['new_password'].strip()
    confirm = request.form['confirm_password'].strip()

    if new_pw != confirm:
        flash('Passwords do not match.', 'danger')
        return redirect(url_for('settings'))

    if len(new_pw) < 6:
        flash('Password must be at least 6 characters.', 'danger')
        return redirect(url_for('settings'))

    conn = get_db()
    conn.execute('UPDATE admin SET password=? WHERE id=?',
                 (generate_password_hash(new_pw), admin_id))
    conn.commit()
    conn.close()
    flash('Password reset successfully.', 'success')
    return redirect(url_for('settings'))

# ── Routes: Camera — Browser webcam recognition (for cloud deploy) ────────────
@app.route('/camera/recognize_frame', methods=['POST'])
@login_required
@csrf.exempt
def recognize_frame():
    """Accept a base64 JPEG frame from the browser webcam, run face recognition,
    and return results as JSON. This enables camera to work on Render/cloud."""
    import base64
    data = request.get_json(silent=True)
    if not data or 'image' not in data:
        return jsonify({'error': 'No image'}), 400

    try:
        # Decode base64 image (strip data:image/jpeg;base64, prefix if present)
        img_data = data['image']
        if ',' in img_data:
            img_data = img_data.split(',', 1)[1]
        img_bytes = base64.b64decode(img_data)

        # Convert to numpy array
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            return jsonify({'error': 'Invalid image'}), 400

        # Run recognition using engine
        scale = engine.FRAME_SCALE
        small = cv2.resize(frame, (0, 0), fx=scale, fy=scale)
        rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        rgb_small = engine._preprocess_frame(rgb_small)

        locations = face_recognition.face_locations(rgb_small, model=DETECTION_MODEL)
        encs = face_recognition.face_encodings(rgb_small, locations, num_jitters=1)

        inv_scale = int(1 / scale)
        results = []
        for enc, loc in zip(encs, locations):
            top, right, bottom, left = loc
            face_w = right - left
            face_h = bottom - top
            if face_w < engine.MIN_FACE_WIDTH or face_h < engine.MIN_FACE_WIDTH:
                continue

            student_id, name, conf = engine._match_face(enc)
            # Scale back to original coordinates
            t, r, b, l = [v * inv_scale for v in loc]

            if student_id:
                # Track consecutive frames for confirmation
                engine._pending_marks[student_id] = \
                    engine._pending_marks.get(student_id, 0) + 1
                marked = False
                if engine._pending_marks[student_id] >= engine.CONFIRM_FRAMES:
                    marked = engine.mark_attendance(student_id, name)

                results.append({
                    'name': name,
                    'student_id': student_id,
                    'confidence': round(conf * 100),
                    'box': [l, t, r, b],
                    'marked': marked,
                    'known': True
                })
            else:
                results.append({
                    'name': 'Unknown',
                    'student_id': None,
                    'confidence': 0,
                    'box': [l, t, r, b],
                    'marked': False,
                    'known': False
                })

        return jsonify({'faces': results})

    except Exception as e:
        logger.error(f'recognize_frame error: {e}')
        return jsonify({'error': str(e)}), 500

# ── Routes: Camera — Recent marks (AJAX) ─────────────────────────────────────
@app.route('/camera/recent_marks')
@login_required
@csrf.exempt
def recent_marks():
    """Return recently marked students for the camera page live feed."""
    today = date.today().isoformat()
    conn  = get_db()
    rows  = conn.execute('''
        SELECT student_id, name, time FROM attendance
        WHERE date=? ORDER BY time DESC LIMIT 10
    ''', (today,)).fetchall()
    conn.close()
    return jsonify([{'student_id': r['student_id'], 'name': r['name'], 'time': str(r['time'])} for r in rows])

# ── Routes: Student Profile ──────────────────────────────────────────────────
@app.route('/student/<student_id>')
@login_required
def student_profile(student_id):
    conn = get_db()
    student = conn.execute('SELECT * FROM students WHERE student_id=?', (student_id,)).fetchone()
    if not student:
        conn.close()
        flash('Student not found.', 'danger')
        return redirect(url_for('register'))

    # Attendance history
    records = conn.execute('''
        SELECT date, time, status FROM attendance
        WHERE student_id=? ORDER BY date DESC, time DESC LIMIT 50
    ''', (student_id,)).fetchall()

    # Stats
    total_days = conn.execute(
        'SELECT COUNT(DISTINCT date) FROM attendance WHERE student_id=?', (student_id,)
    ).fetchone()[0]
    total_working = conn.execute('SELECT COUNT(DISTINCT date) FROM attendance').fetchone()[0]

    # Monthly breakdown (cross-DB compatible)
    if USE_PG:
        monthly = conn.execute('''
            SELECT to_char(date, 'YYYY-MM') as month, COUNT(DISTINCT date) as days
            FROM attendance WHERE student_id=?
            GROUP BY month ORDER BY month DESC LIMIT 6
        ''', (student_id,)).fetchall()
    else:
        monthly = conn.execute('''
            SELECT strftime('%%Y-%%m', date) as month, COUNT(DISTINCT date) as days
            FROM attendance WHERE student_id=?
            GROUP BY month ORDER BY month DESC LIMIT 6
        ''', (student_id,)).fetchall()

    conn.close()
    pct = round((total_days / total_working * 100), 1) if total_working > 0 else 0

    return render_template('student_profile.html',
                           student=student,
                           records=records,
                           total_days=total_days,
                           total_working=total_working,
                           pct=pct,
                           monthly=monthly)

# ── Routes: Bulk CSV Import ──────────────────────────────────────────────────
@app.route('/bulk-import', methods=['GET', 'POST'])
@login_required
def bulk_import():
    if request.method == 'POST':
        if 'csv_file' not in request.files or request.files['csv_file'].filename == '':
            flash('Please upload a CSV file.', 'danger')
            return redirect(request.url)

        file = request.files['csv_file']
        try:
            df = pd.read_csv(file)
        except Exception as e:
            flash(f'Could not parse CSV: {e}', 'danger')
            return redirect(request.url)

        required = {'student_id', 'name'}
        if not required.issubset(set(df.columns.str.lower().str.strip())):
            flash('CSV must contain at least "student_id" and "name" columns.', 'danger')
            return redirect(request.url)

        df.columns = df.columns.str.lower().str.strip()
        added, skipped, errors = 0, 0, 0

        conn = get_db()
        for _, row in df.iterrows():
            sid  = str(row['student_id']).strip()
            name = str(row['name']).strip()
            if not sid or not name:
                errors += 1
                continue

            email = str(row.get('email', '')).strip() if 'email' in df.columns else ''
            dept  = str(row.get('department', '')).strip() if 'department' in df.columns else ''
            phone = str(row.get('phone', '')).strip() if 'phone' in df.columns else ''

            # Clean up NaN values
            if email == 'nan': email = ''
            if dept  == 'nan': dept  = ''
            if phone == 'nan': phone = ''

            try:
                conn.execute(
                    'INSERT INTO students (student_id, name, email, department, phone) VALUES (?,?,?,?,?)',
                    (sid, name, email, dept, phone)
                )
                added += 1
            except DBIntegrityError:
                if USE_PG:
                    conn.rollback()
                skipped += 1

        conn.commit()
        conn.close()

        log_action('bulk_import', f'{added} students', f'Added: {added}, Skipped: {skipped}, Errors: {errors}')
        flash(f'✅ Import complete — {added} added, {skipped} skipped (duplicate), {errors} errors.', 'success')
        return redirect(url_for('register'))

    return render_template('bulk_import.html')

# ── Routes: Audit Log ────────────────────────────────────────────────────────
@app.route('/audit-log')
@login_required
def audit_log_view():
    conn = get_db()
    logs = conn.execute('''
        SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 100
    ''').fetchall()
    conn.close()
    return render_template('audit_log.html', logs=logs)

# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)