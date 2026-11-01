import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.executescript("""
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

INSERT OR IGNORE INTO users(name, email, password, role, validation)
VALUES ('Admin', 'admin@gmail.com', 'secret', 'admin', '1');

DELETE FROM books;
DELETE FROM sqlite_sequence
WHERE name = 'books';


""")



conn.commit()

cursor.execute("SELECT * FROM users")
print(cursor.fetchall())

conn.close()

print("Database created successfully!")