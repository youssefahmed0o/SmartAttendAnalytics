
import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "database.db"


def get_student_attendance(student_id):
    """حساب إحصائيات الحضور لطالب محدد."""

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        student = conn.execute(
            """
            SELECT id, student_code, full_name
            FROM students
            WHERE id = ?
            """,
            (student_id,),
        ).fetchone()

        if student is None:
            raise ValueError("الطالب غير موجود.")

        rows = conn.execute(
            """
            SELECT attendance_status, COUNT(*) AS total
            FROM attendance
            WHERE student_id = ?
            GROUP BY attendance_status
            """,
            (student_id,),
        ).fetchall()

    counts = {
        "present": 0,
        "late": 0,
        "absent": 0,
        "excused": 0,
    }

    for row in rows:
        counts[row["attendance_status"]] = row["total"]

    # الغياب بعذر لا يدخل في المقام
    counted_sessions = (
        counts["present"]
        + counts["late"]
        + counts["absent"]
    )

    attended_sessions = counts["present"] + counts["late"]

    if counted_sessions > 0:
        attendance_rate = round(
            attended_sessions / counted_sessions * 100,
            2,
        )
    else:
        attendance_rate = 0.0

    return {
        "student_id": student["id"],
        "student_code": student["student_code"],
        "full_name": student["full_name"],
        "present": counts["present"],
        "late": counts["late"],
        "absent": counts["absent"],
        "excused": counts["excused"],
        "counted_sessions": counted_sessions,
        "attendance_rate": attendance_rate,
    }
    
def get_group_attendance(group_id):
    """إرجاع إحصائيات الطلاب داخل مجموعة محددة."""

    with sqlite3.connect(DB_PATH) as conn:
        students = conn.execute(
            """
            SELECT id
            FROM students
            WHERE group_id = ?
            ORDER BY student_code
            """,
            (group_id,),
        ).fetchall()

    report = []

    for student in students:
        stats = get_student_attendance(student[0])
        report.append(stats)

    return report


def get_low_attendance_students(threshold=75):
    """إرجاع الطلاب الذين لديهم سجلات حضور ونسبتهم أقل من الحد المحدد."""

    if not 0 <= threshold <= 100:
        raise ValueError("نسبة الحضور يجب أن تكون بين 0 و100.")

    with sqlite3.connect(DB_PATH) as conn:
        students = conn.execute(
            "SELECT id FROM students ORDER BY student_code"
        ).fetchall()

    low_attendance = []

    for student in students:
        stats = get_student_attendance(student[0])

        # لا نصنّف الطالب قبل وجود سجلات حضور له
        if (
            stats["counted_sessions"] > 0
            and stats["attendance_rate"] < threshold
        ):
            low_attendance.append(stats)

    return low_attendance

