import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash

DB_PATH = Path(__file__).resolve().parent / "database.db"


def seed_database():
    if not DB_PATH.exists():
        print("ERROR: database.db غير موجودة.")
        return

    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        with connection:
            # 1. إنشاء المستخدمين
            users = [
                ("admin", generate_password_hash("123456"), "admin"),
                ("dr_simon", generate_password_hash("123456"), "doctor"),
                ("dr_asmaa", generate_password_hash("123456"), "doctor"),
                ("dr_salah", generate_password_hash("123456"), "doctor"),
                ("dr_sameh", generate_password_hash("123456"), "doctor"),
                ("dr_samy", generate_password_hash("123456"), "doctor"),
                ("student01", generate_password_hash("123456"), "student"),
            ]

            connection.executemany(
                "INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                users
            )

            student_user_id = connection.execute(
                "SELECT id FROM users WHERE username = 'student01'"
            ).fetchone()[0]

            # 2. إدخال المجموعات
            groups = [
                ("الفرقة الثانية - مجموعة 1", 2),
                ("الفرقة الثانية - مجموعة 2", 2),
            ]
            connection.executemany(
                "INSERT OR IGNORE INTO groups (group_name, level) VALUES (?, ?)", groups
            )

            g1_id = connection.execute("SELECT id FROM groups WHERE group_name = 'الفرقة الثانية - مجموعة 1'").fetchone()[0]

            # 3. إدخال الطالب التجريبي
            connection.execute(
                "INSERT OR IGNORE INTO students (student_code, full_name, group_id, user_id) VALUES (?, ?, ?, ?)",
                ("2530540", "يوسف احمد عبد الشافي محمود حسن", g1_id, student_user_id)
            )

            # 4. إدخال المواد الرسمية للفرقة الثانية
            subjects = [
                ("CS201", "Java"),
                ("AI201", "Artificial Intelligence"),
                ("AI202", "Expert Systems"),
                ("DS201", "Data Science Fundamentals"),
                ("AI203", "Artificial Intelligence Applications"),
                ("GEN201", "History of Technology"),
                ("GEN202", "Principles of Technology"),
                ("GEN203", "Occupational Health and Safety"),
            ]
            connection.executemany(
                "INSERT OR IGNORE INTO subjects (subject_code, subject_name) VALUES (?, ?)",
                subjects
            )

            # 5. إدخال المحاضرين
            instructors = [
                ("د. سيمون عزت", "dr_simon"),
                ("د. أسماء الأمين", "dr_asmaa"),
                ("د. محمد صلاح", "dr_salah"),
                ("د. سامح مصطفى", "dr_sameh"),
                ("د. محمود سامي", "dr_samy"),
            ]
            for name, uname in instructors:
                u_id = connection.execute("SELECT id FROM users WHERE username = ?", (uname,)).fetchone()[0]
                connection.execute(
                    "INSERT OR IGNORE INTO instructors (display_name, user_id) VALUES (?, ?)",
                    (name, u_id)
                )

            # 6. إضافة مواعيد للجدول الدراسي (تطبيقي من الجدول الرسمي)
            sub_java = connection.execute("SELECT id FROM subjects WHERE subject_code = 'CS201'").fetchone()[0]
            sub_ai = connection.execute("SELECT id FROM subjects WHERE subject_code = 'AI201'").fetchone()[0]

            schedules = [
                (sub_ai, g1_id, "Sunday", "09:00", "11:00", "every", "A305"),
                (sub_java, g1_id, "Sunday", "11:00", "01:00", "every", "A-New"),
            ]

            connection.executemany(
                """INSERT OR IGNORE INTO schedule 
                   (subject_id, group_id, weekday, start_time, end_time, week_type, room)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                schedules
            )

        print("SUCCESS: Stage 5 seed data populated successfully!")

    except sqlite3.Error as error:
        print("DATABASE ERROR:", error)

    finally:
        connection.close()


if __name__ == "__main__":
    seed_database()
