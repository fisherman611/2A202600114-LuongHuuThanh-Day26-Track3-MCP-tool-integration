from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    cohort TEXT NOT NULL,
    age INTEGER,
    score REAL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    credits INTEGER NOT NULL CHECK (credits > 0)
);

CREATE TABLE IF NOT EXISTS enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    semester TEXT NOT NULL,
    final_score REAL,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);
"""


SEED_STUDENTS = [
    ("Alice Nguyen", "A1", 20, 8.8),
    ("Bao Tran", "A1", 21, 7.4),
    ("Chi Le", "B2", 19, 9.1),
    ("Duc Pham", "B2", 22, 6.9),
]

SEED_COURSES = [
    ("MCP101", "MCP Fundamentals", 3),
    ("DB201", "Applied Databases", 4),
    ("PY150", "Python for Data", 3),
]

SEED_ENROLLMENTS = [
    (1, 1, "2026-S1", 8.5),
    (1, 2, "2026-S1", 9.0),
    (2, 1, "2026-S1", 7.0),
    (3, 3, "2026-S1", 9.4),
    (4, 2, "2026-S1", 6.8),
]


def create_database(db_path: str | Path, reset: bool = False) -> Path:
    database_path = Path(db_path).resolve()
    database_path.parent.mkdir(parents=True, exist_ok=True)

    if reset and database_path.exists():
        database_path.unlink()

    with sqlite3.connect(database_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA_SQL)

        student_count = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        if student_count == 0:
            conn.executemany(
                "INSERT INTO students (full_name, cohort, age, score) VALUES (?, ?, ?, ?)",
                SEED_STUDENTS,
            )

        course_count = conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
        if course_count == 0:
            conn.executemany(
                "INSERT INTO courses (code, title, credits) VALUES (?, ?, ?)",
                SEED_COURSES,
            )

        enrollment_count = conn.execute("SELECT COUNT(*) FROM enrollments").fetchone()[0]
        if enrollment_count == 0:
            conn.executemany(
                """
                INSERT INTO enrollments (student_id, course_id, semester, final_score)
                VALUES (?, ?, ?, ?)
                """,
                SEED_ENROLLMENTS,
            )

        conn.commit()

    return database_path


if __name__ == "__main__":
    default_path = Path(__file__).resolve().parent / "lab.db"
    final_path = create_database(default_path, reset=True)
    print(f"Database initialized: {final_path}")
