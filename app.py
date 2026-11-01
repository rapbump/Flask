from flask import Flask, render_template, url_for, request, session, redirect
import sqlite3

app = Flask(__name__)
app.secret_key = "secret"


@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        cursor.execute("""
            INSERT INTO users (name , email, password)
            VAlUES (?, ?, ?)
            """,
            (name, email, password))
        conn.commit()
        return render_template("login.html")

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        user_email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (user_email, password)
        )


        user = cursor.fetchone()

        if user:

            session["id"] = user[0]
            session["name"] = user[1]
            session["email"] = user[2]
            session["role"] = user[4]

            if session["role"] == "admin":
                cursor.execute("SELECT * FROM users")
                users = cursor.fetchall()

                conn.close()

                return render_template("admin.html" , users=users)

            return render_template("user.html")

    return render_template("login.html")

@app.route("/validation/<int:user_id>", methods = ["GET", "POST"])
def validation(user_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users  SET validation = 1 WHERE id = ?",
        (user_id,)
    )

    conn.commit
    conn.close
    return render_template("admin.html")

@app.route("/add_books", methods = ["GET", "POST"])
def add_books():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    if request.method == "POST":
        book_title = request.form["title"]
        book_author = request.form["author"]
        book_copies = request.form["copies"]

        cursor.execute(
            """
            INSERT INTO books (book_name, book_author, copies) 
            VALUES (?, ?, ?)

            """,
            (book_title, book_author, book_copies))
            
        conn.commit()

    cursor.execute("SELECT * FROM books")
    books = cursor.fetchall()
    
            
    conn.close()
    return render_template("books.html", books=books)


@app.route("/admin")
def admin_dashboard():
    return render_template("admin.html")

@app.route("/borrow_request")
def borrow_req():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT * FROM users 
        WHERE id != 1

        """
    )
    user = cursor.fetchall()
    conn.close()

    return render_template("borrow_request.html", user=user)

@app.route("/user_dashboard")
def user_dashboard():

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM books
    """)
    books = cursor.fetchall()

    cursor.execute("""
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
    """, (session["id"],))

    borrowed = cursor.fetchall()

    conn.close()

    return render_template(
        "user_dashboard.html",
        books=books,
        borrowed=borrowed
    )


@app.route("/return_book/<int:record_id>", methods=["POST"])
def return_book(record_id):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT book_id
        FROM borrowed_records
        WHERE record_id = ?
    """, (record_id,))

    book_id = cursor.fetchone()[0]

    cursor.execute("""
        UPDATE borrowed_records
        SET
            status = 'Returned',
            return_time = CURRENT_TIMESTAMP
        WHERE record_id = ?
    """, (record_id,))

    cursor.execute("""
        UPDATE books
        SET copies = copies + 1
        WHERE book_id = ?
    """, (book_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("user_dashboard"))

@app.route("/request_borrow/<int:book_id>", methods=["POST"])
def request_borrow(book_id):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO borrowed_records(
            user_id,
            book_id,
            status
        )
        VALUES (?, ?, ?)
    """, (
        session["id"],
        book_id,
        "Pending"
    ))

    cursor.execute("""
        UPDATE books
        SET copies = copies - 1
        WHERE book_id = ?
    """, (book_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("user_dashboard"))



if __name__ == "__main__":
    app.run(debug=True)