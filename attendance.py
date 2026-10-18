
import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "database.db"


def create_lecture(subject_id, group_id, lecture_date, start_time, end_time):
    """إنشاء محاضرة جديدة في قاعدة البيانات."""

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        cursor = conn.execute(
            """
            INSERT INTO lectures (
                subject_id,
                group_id,
                lecture_date,
                start_time,
                end_time,
                status
            )
            VALUES (?, ?, ?, ?, ?, 'scheduled')
            """,
            (
                subject_id,
                group_id,
                lecture_date,
                start_time,
                end_time,
            ),
        )

        return cursor.lastrowid



def open_lecture(lecture_id):
    """فتح محاضرة مسجلة مسبقًا لاستقبال الحضور."""

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        cursor = conn.execute(
            """
            UPDATE lectures
            SET status = 'open'
            WHERE id = ? AND status = 'scheduled'
            """,
            (lecture_id,),
        )

        if cursor.rowcount == 0:
            raise ValueError(
                "المحاضرة غير موجودة أو ليست في حالة مجدولة."
            )

    return True


def mark_attendance(lecture_id, student_id, attendance_status):
    """تسجيل حالة طالب مع التحقق من المحاضرة والمجموعة."""

    allowed_statuses = {"present", "late", "absent", "excused"}

    if attendance_status not in allowed_statuses:
        raise ValueError("حالة الحضور غير صحيحة.")

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        lecture = conn.execute(
            """
            SELECT group_id, status
            FROM lectures
            WHERE id = ?
            """,
            (lecture_id,),
        ).fetchone()

        if lecture is None:
            raise ValueError("المحاضرة غير موجودة.")

        if lecture[1] != "open":
            raise ValueError("يجب فتح المحاضرة قبل تسجيل الحضور.")

        student = conn.execute(
            """
            SELECT group_id
            FROM students
            WHERE id = ? AND status = 'active'
            """,
            (student_id,),
        ).fetchone()

        if student is None:
            raise ValueError("الطالب غير موجود أو غير نشط.")

        
        group_membership = conn.execute(
            """
            SELECT 1
            FROM lecture_groups
            WHERE lecture_id = ? AND group_id = ?
            """,
            (lecture_id, student[0]),
        ).fetchone()

        if student[0] != lecture[0] and group_membership is None:
            raise ValueError(
                "لا يمكن تسجيل طالب من مجموعة أخرى."
            )


        cursor = conn.execute(
            """
            INSERT INTO attendance (
                lecture_id,
                student_id,
                attendance_status,
                method
            )
            VALUES (?, ?, ?, 'manual')
            """,
            (lecture_id, student_id, attendance_status),
        )

        return cursor.lastrowid
