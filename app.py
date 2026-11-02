from flask import Flask, render_template, url_for, request, session, redirect
import sqlite3
from pathlib import Path

from models import init_db

app = Flask(__name__)
app.secret_key = "secret"

init_db()


def get_db_connection():
    return sqlite3.connect(Path(__file__).with_name("library.db"))


@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or not password:
            return render_template("signup.html", error="Please complete all fields.")

        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                (name, email, password),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return render_template(
                "signup.html",
                error="That name or email is already registered.",
            )
        conn.close()
        return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    conn = get_db_connection()

    if request.method == "POST":
        user_email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = conn.execute(
            "SELECT * FROM users WHERE email = ? AND password = ?",
            (user_email, password),
        ).fetchone()
        conn.close()

        if user:
            if user[4] != "admin" and str(user[5]) != "1":
                return render_template(
                    "login.html",
                    error="Your account is awaiting admin validation.",
                )

            session.clear()
            session["id"] = user[0]
            session["name"] = user[1]
            session["email"] = user[2]
            session["role"] = user[4]

            if session["role"] == "admin":
                return redirect(url_for("admin_dashboard"))

            return redirect(url_for("user_dashboard"))

        return render_template("login.html", error="Invalid email or password.")

    conn.close()
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/validation/<int:user_id>", methods=["POST"])
def validation(user_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    conn.execute(
        "UPDATE users SET validation = 1 WHERE id = ?",
        (user_id,),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("admin_dashboard"))


@app.route("/add_books", methods=["GET", "POST"])
def add_books():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    if request.method == "POST":
        book_title = request.form.get("title", "").strip()
        book_author = request.form.get("author", "").strip()
        try:
            book_copies = int(request.form.get("copies", ""))
        except ValueError:
            book_copies = -1

        if not book_title or not book_author or book_copies < 0:
            books = conn.execute("SELECT * FROM books").fetchall()
            conn.close()
            return render_template(
                "books.html",
                books=books,
                error="Enter a title, author, and a non-negative whole number of copies.",
            )

        conn.execute(
            "INSERT INTO books (book_name, book_author, copies) VALUES (?, ?, ?)",
            (book_title, book_author, book_copies),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("add_books"))

    books = conn.execute("SELECT * FROM books").fetchall()
    conn.close()
    return render_template("books.html", books=books)


@app.route("/admin")
def admin_dashboard():
    conn = get_db_connection()
    if session.get("role") != "admin":
        conn.close()
        return redirect(url_for("login"))
    users = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return render_template("admin.html", users=users)


@app.route("/borrow_request")
def borrow_req():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    borrow_requests = conn.execute(
        """
        SELECT borrowed_records.record_id, users.name, books.book_name,
               borrowed_records.borrowed_time, borrowed_records.status
        FROM borrowed_records
        JOIN users ON users.id = borrowed_records.user_id
        JOIN books ON books.book_id = borrowed_records.book_id
        ORDER BY borrowed_records.record_id DESC
        """
    ).fetchall()
    conn.close()
    return render_template("borrow_request.html", borrow_requests=borrow_requests)


@app.route("/user_dashboard")
def user_dashboard():
    if session.get("id") is None or session.get("role") == "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    books = conn.execute("SELECT * FROM books").fetchall()
    borrowed = conn.execute("""
        SELECT
            borrowed_records.record_id,
            books.book_name,
            borrowed_records.status,
            borrowed_records.borrowed_time,
            borrowed_records.return_time
        FROM borrowed_records
        JOIN books
        ON borrowed_records.book_id = books.book_id
        WHERE borrowed_records.user_id = ?
        ORDER BY borrowed_records.record_id DESC
    """, (session["id"],)).fetchall()
    conn.close()

    return render_template(
        "user_dashboard.html",
        books=books,
        borrowed=borrowed
    )


@app.route("/return_book/<int:record_id>", methods=["POST"])
def return_book(record_id):
    if session.get("id") is None or session.get("role") == "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    record = conn.execute("""
        SELECT book_id
        FROM borrowed_records
        WHERE record_id = ? AND user_id = ? AND status = 'Approved'
    """, (record_id, session["id"])).fetchone()

    if record is None:
        conn.close()
        return redirect(url_for("user_dashboard"))

    cursor = conn.execute("""
        UPDATE borrowed_records
        SET
            status = 'Returned',
            return_time = CURRENT_TIMESTAMP
        WHERE record_id = ? AND user_id = ? AND status = 'Approved'
    """, (record_id, session["id"]))

    if cursor.rowcount:
        conn.execute("""
            UPDATE books
            SET copies = copies + 1
            WHERE book_id = ?
        """, (record[0],))

    conn.commit()
    conn.close()

    return redirect(url_for("user_dashboard"))


@app.route("/request_borrow/<int:book_id>", methods=["POST"])
def request_borrow(book_id):
    if session.get("id") is None or session.get("role") == "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.execute("""
        UPDATE books
        SET copies = copies - 1
        WHERE book_id = ? AND copies > 0
    """, (book_id,))

    if cursor.rowcount:
        conn.execute("""
            INSERT INTO borrowed_records (user_id, book_id, status)
            VALUES (?, ?, 'Pending')
        """, (session["id"], book_id))
        conn.commit()
    conn.close()

    return redirect(url_for("user_dashboard"))


@app.route("/approve_borrow/<int:record_id>", methods=["POST"])
def approve_borrow(record_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    conn.execute(
        "UPDATE borrowed_records SET status = 'Approved' "
        "WHERE record_id = ? AND status = 'Pending'",
        (record_id,),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("borrow_req"))


@app.route("/reject_borrow/<int:record_id>", methods=["POST"])
def reject_borrow(record_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    record = conn.execute(
        "SELECT book_id FROM borrowed_records "
        "WHERE record_id = ? AND status = 'Pending'",
        (record_id,),
    ).fetchone()
    if record:
        cursor = conn.execute(
            "UPDATE borrowed_records SET status = 'Rejected' "
            "WHERE record_id = ? "
            "AND status = 'Pending'",
            (record_id,),
        )
        if cursor.rowcount:
            conn.execute(
                "UPDATE books SET copies = copies + 1 WHERE book_id = ?",
                (record[0],),
            )
            conn.commit()
    conn.close()
    return redirect(url_for("borrow_req"))


if __name__ == "__main__":
    app.run(debug=True)
