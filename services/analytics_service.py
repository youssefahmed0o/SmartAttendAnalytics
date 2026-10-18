import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "database.db"

def get_student_analytics(student_id):
    """حساب نسبة حضور وغياب الطالب لكل مادة مقيد بها."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        
        # جلب مجموعة الطالب
        student = conn.execute("SELECT group_id FROM students WHERE id = ?", (student_id,)).fetchone()
        if not student:
            return []

        # جلب المواد والمحاضرات المنعقدة الخاصة بمجموعته
        query = """
            SELECT 
                sub.id AS subject_id,
                sub.subject_name,
                COUNT(DISTINCT l.id) AS total_lectures,
                COUNT(DISTINCT CASE WHEN a.attendance_status = 'present' THEN a.lecture_id END) AS attended_lectures
            FROM subjects sub
            JOIN lectures l ON sub.id = l.subject_id AND l.group_id = ?
            LEFT JOIN attendance a ON l.id = a.lecture_id AND a.student_id = ?
            GROUP BY sub.id, sub.subject_name
        """
        records = conn.execute(query, (student['group_id'], student_id)).fetchall()

        analytics = []
        for r in records:
            total = r['total_lectures']
            attended = r['attended_lectures']
            absent = total - attended
            percentage = round((attended / total * 100), 1) if total > 0 else 100.0
            
            # نظام التنبيه المبكر (تحذير إذا غاب أكثر من 25% من المحاضرات)
            warning = False
            if total > 0 and (absent / total) >= 0.25:
                warning = True

            analytics.append({
                'subject_name': r['subject_name'],
                'total_lectures': total,
                'attended_lectures': attended,
                'absent_lectures': absent,
                'attendance_percentage': percentage,
                'warning': warning
            })
            
        return analytics

def get_doctor_analytics(instructor_id):
    """إحصائيات إجمالية للدكتور عن المحاضرات المسجلة في النظام."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        
        query = """
            SELECT 
                sub.subject_name,
                g.group_name,
                COUNT(DISTINCT l.id) AS total_sessions,
                COUNT(a.id) AS total_attendances
            FROM lectures l
            JOIN subjects sub ON l.subject_id = sub.id
            JOIN groups g ON l.group_id = g.id
            LEFT JOIN attendance a ON a.lecture_id = l.id AND a.attendance_status = 'present'
            GROUP BY sub.id, g.id
        """
        return conn.execute(query).fetchall()
