import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database.db"


def create_database():
    connection = sqlite3.connect(DB_PATH)

    try:
        connection.execute("PRAGMA foreign_keys = ON")

        connection.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('student', 'doctor', 'admin')),
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_name TEXT NOT NULL UNIQUE,
            level INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_code TEXT NOT NULL UNIQUE,
            full_name TEXT NOT NULL,
            group_id INTEGER NOT NULL,
            user_id INTEGER UNIQUE,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (group_id) REFERENCES groups(id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_code TEXT UNIQUE,
            subject_name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS instructors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            display_name TEXT NOT NULL,
            user_id INTEGER UNIQUE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS teaching_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            group_id INTEGER NOT NULL,
            instructor_id INTEGER NOT NULL,
            FOREIGN KEY (subject_id) REFERENCES subjects(id),
            FOREIGN KEY (group_id) REFERENCES groups(id),
            FOREIGN KEY (instructor_id) REFERENCES instructors(id),
            UNIQUE (subject_id, group_id, instructor_id)
        );

        CREATE TABLE IF NOT EXISTS schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER,
            subject_id INTEGER NOT NULL,
            group_id INTEGER NOT NULL,
            weekday TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            week_type TEXT NOT NULL DEFAULT 'every',
            room TEXT,
            FOREIGN KEY (assignment_id) REFERENCES teaching_assignments(id),
            FOREIGN KEY (subject_id) REFERENCES subjects(id),
            FOREIGN KEY (group_id) REFERENCES groups(id),
            CHECK (start_time < end_time),
            CHECK (week_type IN ('every', 'week1', 'week2'))
        );

        CREATE TABLE IF NOT EXISTS lectures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            group_id INTEGER NOT NULL,
            lecture_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'scheduled',
            created_by INTEGER,
            FOREIGN KEY (subject_id) REFERENCES subjects(id),
            FOREIGN KEY (group_id) REFERENCES groups(id),
            FOREIGN KEY (created_by) REFERENCES users(id),
            CHECK (status IN ('scheduled', 'open', 'closed'))
        );

        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lecture_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            attendance_status TEXT NOT NULL DEFAULT 'present',
            marked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            method TEXT NOT NULL DEFAULT 'manual',
            FOREIGN KEY (lecture_id) REFERENCES lectures(id),
            FOREIGN KEY (student_id) REFERENCES students(id),
            UNIQUE (lecture_id, student_id),
            CHECK (attendance_status IN ('present', 'late', 'absent', 'excused'))
        );
        
        CREATE TABLE IF NOT EXISTS qr_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lecture_id INTEGER NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL,
    is_used INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (lecture_id) REFERENCES lectures(id)
       );
        """)

        connection.commit()
        print("Database updated for Stage 5 successfully!")

    finally:
        connection.close()


if __name__ == "__main__":
    create_database()
