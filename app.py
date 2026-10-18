import os
import sqlite3
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash

# استيراد الخدمات والدوال الخارجية في أعلى الملف
from services.analytics_service import get_student_analytics, get_doctor_analytics
from services.qr_service import generate_qr_token, verify_qr_token
from attendance import create_lecture, open_lecture, mark_attendance
# إعداد تطبيق Flask ومفتاح الجلسات من متغير البيئة
app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY")

if not app.config["SECRET_KEY"]:
    raise RuntimeError(
        "FLASK_SECRET_KEY is not configured. "
        "Set it before starting the application."
    )
# مسار قاعدة البيانات SQLite
DB_PATH = Path(__file__).resolve().parent / "database.db"

def get_db_connection():
    """إنشاء اتصال بقاعدة البيانات مع تفعيل وضع التحمل العالي WAL والمفاتيح الأجنبية."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


# ==========================================
# 1. مسار الصفحة الرئيسية وتوجيه المستخدمين حسب أدوارهم
# ==========================================
@app.route("/")
def index():
    if "user_id" in session:
        role = session.get("role")
        if role == "student":
            return redirect(url_for("student_dashboard"))
        elif role == "doctor":
            return redirect(url_for("doctor_dashboard"))
        elif role == "admin":
            return redirect(url_for("admin_dashboard"))
    return redirect(url_for("login"))


# ==========================================
# 2. نظام تسجيل الدخول وتسجيل الخروج
# ==========================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? AND is_active = 1",
            (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            if user["role"] == "student":
                return redirect(url_for("student_dashboard"))
            elif user["role"] == "doctor":
                return redirect(url_for("doctor_dashboard"))
            elif user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
        else:
            flash("اسم المستخدم أو كلمة المرور غير صحيحة.", "danger")

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


# ==========================================
# 3. لوحة تحكم الطالب
# ==========================================
@app.route("/student")
def student_dashboard():
    if "user_id" not in session or session.get("role") != "student":
        return redirect(url_for("login"))

    conn = get_db_connection()
    student = conn.execute(
        "SELECT * FROM students WHERE user_id = ?", (session["user_id"],)
    ).fetchone()

    schedule_items = []
    open_lectures = []
    my_attendance = []

    if student:
        schedule_items = conn.execute(
            """
            SELECT s.weekday, s.start_time, s.end_time, s.room, sub.subject_name
            FROM schedule s
            JOIN subjects sub ON s.subject_id = sub.id
            WHERE s.group_id = ?
            ORDER BY s.weekday, s.start_time
            """,
            (student["group_id"],)
        ).fetchall()

        open_lectures = conn.execute(
            """
            SELECT DISTINCT l.id, sub.subject_name, l.lecture_date, l.start_time, l.end_time
            FROM lectures l
            JOIN subjects sub ON l.subject_id = sub.id
            JOIN lecture_groups lg ON l.id = lg.lecture_id
            WHERE lg.group_id = ? AND l.status = 'open'
            """,
            (student["group_id"],)
        ).fetchall()

        my_attendance = conn.execute(
            """
            SELECT l.id AS lecture_id, sub.subject_name, l.lecture_date, a.attendance_status, a.marked_at
            FROM attendance a
            JOIN lectures l ON a.lecture_id = l.id
            JOIN subjects sub ON l.subject_id = sub.id
            WHERE a.student_id = ?
            ORDER BY a.marked_at DESC
            """,
            (student["id"],)
        ).fetchall()

    conn.close()
    return render_template(
        "student_dashboard.html",
        student=student,
        schedule=schedule_items,
        open_lectures=open_lectures,
        my_attendance=my_attendance,
    )


@app.route("/attendance/mark", methods=["POST"])
def handle_mark_attendance():
    if "user_id" not in session or session.get("role") != "student":
        return redirect(url_for("login"))

    lecture_id = request.form.get("lecture_id")
    conn = get_db_connection()
    student = conn.execute(
        "SELECT id FROM students WHERE user_id = ?", (session["user_id"],)
    ).fetchone()
    conn.close()

    if not student:
        flash("حساب الطالب غير مرتبط بسجل أكاديمي.", "danger")
        return redirect(url_for("student_dashboard"))

    try:
        mark_attendance(lecture_id, student["id"], "present")
        flash("تم تسجيل حضورك بنجاح! ✅", "success")
    except sqlite3.IntegrityError:
        flash("لقد قمت بتسجيل الحضور لهذه المحاضرة بالفعل مسبقاً! ⚠️", "warning")
    except Exception as e:
        flash(f"فشل تسجيل الحضور: {e}", "danger")

    return redirect(url_for("student_dashboard"))

# ==========================================
# 4. لوحة تحكم الدكتور
# ==========================================
@app.route("/doctor")
def doctor_dashboard():
    if "user_id" not in session or session.get("role") != "doctor":
        return redirect(url_for("login"))

    conn = get_db_connection()
    
    # جلب بيانات الدكتور المرتبطة بحساب المستخدم الحالي
    instructor = conn.execute(
        "SELECT * FROM instructors WHERE user_id = ?", (session["user_id"],)
    ).fetchone()

    if not instructor:
        flash("حساب الدكتور غير مرتبط بسجل أكاديمي.", "danger")
        conn.close()
        return redirect(url_for("login"))
    # جلب المواد المسندة لهذا الدكتور فقط (تعديل استعلام الـ SELECT)
    subjects = conn.execute(
        """
        SELECT sub.id, sub.subject_name 
        FROM subjects sub
        JOIN instructor_subjects isub ON sub.id = isub.subject_id
        WHERE isub.instructor_id = ?
        """,
        (instructor["id"],)
    ).fetchall()

    groups = conn.execute("SELECT * FROM groups").fetchall()

    # جلب المحاضرات الخاصة بمواد هذا الدكتور فقط
    lectures = conn.execute(
        """
        SELECT l.id, sub.subject_name, l.lecture_date, l.start_time, l.end_time, l.status
        FROM lectures l
        JOIN subjects sub ON l.subject_id = sub.id
        JOIN instructor_subjects isub ON sub.id = isub.subject_id
        WHERE isub.instructor_id = ?
        ORDER BY l.id DESC
        """,
        (instructor["id"],)
    ).fetchall()
    
    conn.close()

    return render_template(
        "doctor_dashboard.html",
        instructor=instructor,
        subjects=subjects,
        groups=groups,
        lectures=lectures,
    )


@app.route("/lectures/create", methods=["POST"])
def handle_create_lecture():
    if "user_id" not in session or session.get("role") != "doctor":
        return redirect(url_for("login"))

    subject_id = request.form.get("subject_id")
    group_ids = request.form.getlist("group_ids")
    lecture_date = request.form.get("lecture_date")
    start_time = request.form.get("start_time")
    end_time = request.form.get("end_time")

    if not group_ids:
        flash("يجب اختيار مجموعة واحدة على الأقل!", "danger")
        return redirect(url_for("doctor_dashboard"))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        primary_group_id = group_ids[0]

        cursor.execute(
            """
            INSERT INTO lectures (subject_id, group_id, lecture_date, start_time, end_time, status)
            VALUES (?, ?, ?, ?, ?, 'scheduled')
            """,
            (subject_id, primary_group_id, lecture_date, start_time, end_time)
        )
        lecture_id = cursor.lastrowid

        for g_id in group_ids:
            cursor.execute(
                "INSERT INTO lecture_groups (lecture_id, group_id) VALUES (?, ?)",
                (lecture_id, g_id)
            )
            
        conn.commit()
        conn.close()
        flash("تم إنشاء المحاضرة وتخصيصها للمجموعات المختارة بنجاح!", "success")
    except Exception as e:
        flash(f"حدث خطأ أثناء إنشاء المحاضرة: {e}", "danger")

    return redirect(url_for("doctor_dashboard"))


@app.route("/lectures/open/<int:lecture_id>", methods=["POST"])
def handle_open_lecture(lecture_id):
    if "user_id" not in session or session.get("role") != "doctor":
        return redirect(url_for("login"))
    try:
        open_lecture(lecture_id)
        flash("تم فتح المحاضرة لاستقبال الحضور!", "success")
    except Exception as e:
        flash(f"خطأ: {e}", "danger")
    return redirect(url_for("doctor_dashboard"))


@app.route("/lectures/<int:lecture_id>/close", methods=["POST"])
def handle_close_lecture(lecture_id):
    if "user_id" not in session or session.get("role") != "doctor":
        return redirect(url_for("login"))
    
    conn = get_db_connection()
    conn.execute("UPDATE lectures SET status = 'closed' WHERE id = ?", (lecture_id,))
    conn.commit()
    conn.close()
    flash("تم إغلاق تسجيل الحضور للمحاضرة بنجاح.", "success")
    return redirect(url_for("doctor_dashboard"))


@app.route("/lectures/<int:lecture_id>/get-qr")
def get_lecture_qr(lecture_id):
    if "user_id" not in session or session.get("role") != "doctor":
        return {"error": "غير مصرح"}, 403
    token = generate_qr_token(lecture_id, valid_seconds=30)
    return {"token": token, "lecture_id": lecture_id}


@app.route("/attendance/mark-qr", methods=["POST"])
def handle_mark_attendance_qr():
    if "user_id" not in session or session.get("role") != "student":
        return redirect(url_for("login"))

    lecture_id = request.form.get("lecture_id")
    qr_token = request.form.get("qr_token")
    is_valid, msg = verify_qr_token(lecture_id, qr_token)
    if not is_valid:
        flash(f"فشل التسجيل: {msg}", "danger")
        return redirect(url_for("student_dashboard"))

    conn = get_db_connection()
    student = conn.execute(
        "SELECT id FROM students WHERE user_id = ?", (session["user_id"],)
    ).fetchone()
    conn.close()

    if not student:
        flash("حساب الطالب غير مرتبط بسجل أكاديمي.", "danger")
        return redirect(url_for("student_dashboard"))

    try:
        mark_attendance(lecture_id, student["id"], "present")
        flash("تم تسجيل حضورك بنجاح عبر الـ QR! 📲✅", "success")
    except sqlite3.IntegrityError:
        flash("لقد قمت بتسجيل الحضور لهذه المحاضرة بالفعل مسبقاً! ⚠️", "warning")
    except Exception as e:
        flash(f"حدث خطأ: {e}", "danger")

    return redirect(url_for("student_dashboard"))


# ==========================================
# 5. صفحات التحليلات
# ==========================================
@app.route("/student/analytics")
def student_analytics_page():
    if "user_id" not in session or session.get("role") != "student":
        return redirect(url_for("login"))
    conn = get_db_connection()
    student = conn.execute(
        "SELECT id, full_name FROM students WHERE user_id = ?", (session["user_id"],)
    ).fetchone()
    conn.close()
    if not student:
        flash("حساب الطالب غير مرتبط بسجل أكاديمي.", "danger")
        return redirect(url_for("student_dashboard"))
    reports = get_student_analytics(student["id"])
    return render_template("student_analytics.html", student=student, reports=reports)


@app.route("/doctor/analytics")
def doctor_analytics_page():
    if "user_id" not in session or session.get("role") != "doctor":
        return redirect(url_for("login"))
    conn = get_db_connection()
    instructor = conn.execute(
        "SELECT id, display_name FROM instructors WHERE user_id = ?", (session["user_id"],)
    ).fetchone()
    conn.close()
    if not instructor:
        flash("حساب الدكتور غير مرتبط بسجل أكاديمي.", "danger")
        return redirect(url_for("doctor_dashboard"))
    reports = get_doctor_analytics(instructor["id"])
    return render_template("doctor_analytics.html", instructor=instructor, reports=reports)


# ==========================================
# 6. لوحة تحكم الأدمن والصلاحيات
# ==========================================
@app.route("/admin")
def admin_dashboard():
    if "user_id" not in session or session.get("role") != "admin":
        return redirect(url_for("login"))
    return render_template("base.html")


@app.route("/health")
def health():
    return {"project": "SmartAttend Analytics", "status": "running"}


# صفحة إدارة المستخدمين والحسابات (القديمة كما هي تماماً)
@app.route('/admin/users', methods=['GET'])
def manage_users():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("غير مسموح لك بالدخول لهذه الصفحة.", "danger")
        return redirect(url_for('login'))
        
    with get_db_connection() as conn:
        users = conn.execute("""
            SELECT u.id, u.username, u.role, 
                   COALESCE(s.full_name, i.display_name, 'مشرف النظام') as name
            FROM users u
            LEFT JOIN students s ON u.id = s.user_id
            LEFT JOIN instructors i ON u.id = i.user_id
        """).fetchall()
        
    return render_template('manage_users.html', users=users)


# صفحة مستقلة جديدة لإدارة ومراقبة المحاضرات للأدمن
@app.route('/admin/lectures', methods=['GET'])
def admin_lectures_page():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("غير مسموح لك بالدخول لهذه الصفحة.", "danger")
        return redirect(url_for('login'))
        
    with get_db_connection() as conn:
        lectures = conn.execute("""
            SELECT l.id, sub.subject_name, l.lecture_date, l.start_time, l.end_time, l.status
            FROM lectures l
            JOIN subjects sub ON l.subject_id = sub.id
            ORDER BY l.id DESC
        """).fetchall()
        
    return render_template('admin_lectures.html', lectures=lectures)


# عرض تفاصيل حضور الطلاب لمُحاضرة معينة بواسطة الأدمن
@app.route("/admin/lectures/<int:lecture_id>/attendance")
def admin_lecture_attendance_details(lecture_id):
    if "user_id" not in session or session.get("role") != "admin":
        flash("غير مسموح لك بالدخول.", "danger")
        return redirect(url_for("login"))
        
    conn = get_db_connection()
    lecture = conn.execute(
        """
        SELECT l.id, sub.subject_name, l.lecture_date, l.start_time, l.end_time, l.status
        FROM lectures l
        JOIN subjects sub ON l.subject_id = sub.id
        WHERE l.id = ?
        """,
        (lecture_id,)
    ).fetchone()
    
    attendees = conn.execute(
        """
        SELECT s.full_name, s.student_code, g.group_name, a.attendance_status, a.marked_at
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        LEFT JOIN groups g ON s.group_id = g.id
        WHERE a.lecture_id = ?
        ORDER BY a.marked_at DESC
        """,
        (lecture_id,)
    ).fetchall()
    conn.close()
    
    return render_template("admin_lecture_attendance_details.html", lecture=lecture, attendees=attendees)


# حذف محاضرة بواسطة الأدمن (يعيد التوجيه لصفحة إدارة المحاضرات المستقلة)
@app.route("/admin/lectures/delete/<int:lecture_id>", methods=["POST"])
def admin_delete_lecture(lecture_id):
    if "user_id" not in session or session.get("role") != "admin":
        flash("غير مصرح لك بذلك.", "danger")
        return redirect(url_for("login"))
    
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # إيقاف التحقق من المفاتيح الأجنبية مؤقتاً لتجنب تعارض القيود
            cursor.execute("PRAGMA foreign_keys = OFF;")
            
            # حذف السجلات من كافة الجداول المرتبطة بالمحاضرة
            cursor.execute("DELETE FROM lecture_groups WHERE lecture_id = ?", (lecture_id,))
            cursor.execute("DELETE FROM attendance WHERE lecture_id = ?", (lecture_id,))
            cursor.execute("DELETE FROM lectures WHERE id = ?", (lecture_id,))
            
            # إعادة تفعيل التحقق من المفاتيح الأجنبية
            cursor.execute("PRAGMA foreign_keys = ON;")
            conn.commit()
            
        flash("تم حذف المحاضرة وسجلاتها بنجاح بواسطة المشرف.", "success")
    except Exception as e:
        flash(f"فشل حذف المحاضرة: {e}", "danger")
        
    return redirect(url_for("admin_lectures_page"))


@app.route('/admin/users/add', methods=['POST'])
def add_user():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("غير مصرح لك بذلك.", "danger")
        return redirect(url_for('login'))

    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role') 
    full_name = request.form.get('full_name', '')
    group_id = request.form.get('group_id', 1)  # استقبال رقم المجموعة المختار من النموذج[span_1](start_span)[span_1](end_span)
    
    if not username or not password or not role:
        flash("جميع الحقول الأساسية مطلوبة!", "danger")
        return redirect(url_for('manage_users'))
        
    pwd_hash = generate_password_hash(password)
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (username, pwd_hash, role)
            )
            user_id = cursor.lastrowid
            
            if role == 'student':
                cursor.execute(
                    "INSERT INTO students (user_id, full_name, student_code, group_id) VALUES (?, ?, ?, ?)",
                    (user_id, full_name, username, group_id)
                )
            elif role == 'doctor':
                cursor.execute(
                    "INSERT INTO instructors (user_id, display_name) VALUES (?, ?)",
                    (user_id, full_name)
                )
            conn.commit()
        flash("تم إضافة المستخدم بنجاح!", "success")
    except sqlite3.IntegrityError:
        flash("فشل الإضافة: اسم المستخدم أو كود الطالب مسجل مسبقاً في النظام، يرجى اختيار كود آخر.", "danger")
    except Exception as e:
        flash(f"حدث خطأ أثناء الإضافة: {e}", "danger")
        
    return redirect(url_for('manage_users'))


@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("غير مصرح لك بذلك.", "danger")
        return redirect(url_for('login'))

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM students WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM instructors WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
        flash("تم حذف المستخدم بنجاح.", "success")
    except Exception as e:
        flash(f"فشل الحذف: {e}", "danger")
        
    return redirect(url_for('manage_users'))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
