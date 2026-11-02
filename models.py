import sqlite3
from pathlib import Path


DATABASE = Path(__file__).with_name("library.db")


def init_db():
    conn = sqlite3.connect(DATABASE)
    try:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            validation TEXT NOT NULL DEFAULT '0'
        );

        CREATE TABLE IF NOT EXISTS books (
            book_id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_name TEXT NOT NULL,
            book_author TEXT NOT NULL,
            copies INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS borrowed_records (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            status TEXT DEFAULT 'Pending',
            borrowed_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            return_time DATETIME,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(book_id) REFERENCES books(book_id)
        );
        """)

        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(borrowed_records)")
        }
        if "status" not in columns:
            conn.execute(
                "ALTER TABLE borrowed_records ADD COLUMN status TEXT DEFAULT 'Pending'"
            )
        if "return_time" not in columns:
            conn.execute(
                "ALTER TABLE borrowed_records ADD COLUMN return_time DATETIME"
            )

        conn.execute(
            """
            INSERT OR IGNORE INTO users(name, email, password, role, validation)
            VALUES ('Admin', 'admin@gmail.com', 'secret', 'admin', '1')
            """
        )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print("Database created successfully!")
