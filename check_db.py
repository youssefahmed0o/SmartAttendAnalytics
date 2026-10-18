import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "database.db"

def check_data():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        
        print("--- فحص جدول المستخدمين والدكاترة ---")
        instructors = conn.execute("SELECT i.id, i.user_id, i.display_name, u.username FROM instructors i JOIN users u ON i.user_id = u.id").fetchall()
        for inst in instructors:
            print(f"ID: {inst['id']} | Name: {inst['display_name']} | Username: {inst['username']}")
            
        print("\n--- فحص جدول المواد ---")
        subjects = conn.execute("SELECT * FROM subjects").fetchall()
        for sub in subjects:
            print(f"Subject ID: {sub['id']} | Name: {sub['subject_name']}")
            
        print("\n--- فحص جدول الربط (instructor_subjects) ---")
        links = conn.execute("""
            i.id as inst_id, i.display_name, s.subject_name 
            FROM instructor_subjects isub
            JOIN instructors i ON isub.instructor_id = i.id
            JOIN subjects s ON isub.subject_id = s.id
        """).fetchall()
        for l in links:
            print(f"الدكتور: {l['display_name']} -> مرتبط بالمادة: {l['subject_name']}")

if __name__ == "__main__":
    check_data()
