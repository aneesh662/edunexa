
import os
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "tutorial.db"))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'student',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        level TEXT NOT NULL DEFAULT 'Beginner',
        thumbnail TEXT DEFAULT '',
        instructor_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(instructor_id) REFERENCES users(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS lessons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        video_url TEXT DEFAULT '',
        duration TEXT DEFAULT '',
        lesson_order INTEGER DEFAULT 1,
        FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS enrollments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        course_id INTEGER NOT NULL,
        enrolled_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, course_id),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        lesson_id INTEGER NOT NULL,
        completed INTEGER DEFAULT 0,
        completed_at TEXT,
        UNIQUE(user_id, lesson_id),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS quizzes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quiz_id INTEGER NOT NULL,
        question TEXT NOT NULL,
        option_a TEXT NOT NULL,
        option_b TEXT NOT NULL,
        option_c TEXT NOT NULL,
        option_d TEXT NOT NULL,
        answer TEXT NOT NULL,
        FOREIGN KEY(quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS quiz_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        quiz_id INTEGER NOT NULL,
        score INTEGER NOT NULL,
        total INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
    );
    """)
    # Demo users
    demo = [
        ("Administrator", "admin@example.com", "admin123", "admin"),
        ("Demo Student", "student@example.com", "student123", "student"),
        ("Demo Instructor", "instructor@example.com", "instructor123", "instructor"),
    ]
    for name, email, password, role in demo:
        exists = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if not exists:
            conn.execute("INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)",
                         (name, email, generate_password_hash(password), role))

    instructor = conn.execute("SELECT id FROM users WHERE email='instructor@example.com'").fetchone()
    count = conn.execute("SELECT COUNT(*) AS c FROM courses").fetchone()["c"]
    if count == 0:
        courses = [
            ("Python for Beginners", "Learn Python fundamentals through practical examples.", "Programming", "Beginner", "https://images.unsplash.com/photo-1515879218367-8466d910aaa4?w=800", instructor["id"]),
            ("Excel Data Analysis", "Master Excel formulas, tables, PivotTables and dashboards.", "Data Analytics", "Beginner", "https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=800", instructor["id"]),
            ("Power BI Essentials", "Build professional dashboards and understand business KPIs.", "Business Intelligence", "Intermediate", "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800", instructor["id"]),
        ]
        for c in courses:
            cur = conn.execute("""INSERT INTO courses(title,description,category,level,thumbnail,instructor_id)
                                  VALUES(?,?,?,?,?,?)""", c)
            cid = cur.lastrowid
            lesson_data = [
                ("Introduction", "Course introduction and learning objectives.", "", "8 min", 1),
                ("Core Concepts", "Learn the most important concepts with examples.", "", "15 min", 2),
                ("Practical Exercise", "Complete a small practical exercise.", "", "20 min", 3),
            ]
            for title, desc, video, duration, order_no in lesson_data:
                conn.execute("""INSERT INTO lessons(course_id,title,description,video_url,duration,lesson_order)
                                VALUES(?,?,?,?,?,?)""", (cid, title, desc, video, duration, order_no))
            q = conn.execute("INSERT INTO quizzes(course_id,title) VALUES(?,?)", (cid, "Knowledge Check"))
            qid = q.lastrowid
            conn.execute("""INSERT INTO questions(quiz_id,question,option_a,option_b,option_c,option_d,answer)
                            VALUES(?,?,?,?,?,?,?)""",
                         (qid, "Which option is used to store text in Python?",
                          "String", "Integer", "Boolean", "List", "a"))
    conn.commit()
    conn.close()

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped

def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator

@app.context_processor
def inject_user():
    return {"current_user": session}

@app.route("/")
def index():
    conn = get_db()
    courses = conn.execute("""
        SELECT c.*, u.name AS instructor,
        (SELECT COUNT(*) FROM lessons l WHERE l.course_id=c.id) AS lesson_count
        FROM courses c LEFT JOIN users u ON u.id=c.instructor_id
        ORDER BY c.id DESC LIMIT 6
    """).fetchall()
    conn.close()
    return render_template("index.html", courses=courses)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        if not name or not email or len(password) < 6:
            flash("Enter your name, a valid email and a password of at least 6 characters.", "danger")
            return render_template("register.html")
        conn = get_db()
        try:
            conn.execute("INSERT INTO users(name,email,password) VALUES(?,?,?)",
                         (name, email, generate_password_hash(password)))
            conn.commit()
        except sqlite3.IntegrityError:
            flash("An account with that email already exists.", "danger")
            conn.close()
            return render_template("register.html")
        conn.close()
        flash("Account created. Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))

@app.route("/courses")
def courses():
    q = request.args.get("q","").strip()
    category = request.args.get("category","").strip()
    conn = get_db()
    sql = """SELECT c.*, u.name AS instructor,
             (SELECT COUNT(*) FROM lessons l WHERE l.course_id=c.id) AS lesson_count
             FROM courses c LEFT JOIN users u ON u.id=c.instructor_id WHERE 1=1"""
    params = []
    if q:
        sql += " AND (c.title LIKE ? OR c.description LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    if category:
        sql += " AND c.category=?"
        params.append(category)
    sql += " ORDER BY c.id DESC"
    rows = conn.execute(sql, params).fetchall()
    categories = conn.execute("SELECT DISTINCT category FROM courses ORDER BY category").fetchall()
    conn.close()
    return render_template("courses.html", courses=rows, categories=categories, q=q, category=category)

@app.route("/course/<int:course_id>")
def course_detail(course_id):
    conn = get_db()
    course = conn.execute("""SELECT c.*, u.name AS instructor FROM courses c
                             LEFT JOIN users u ON u.id=c.instructor_id WHERE c.id=?""", (course_id,)).fetchone()
    if not course:
        conn.close()
        abort(404)
    lessons = conn.execute("SELECT * FROM lessons WHERE course_id=? ORDER BY lesson_order,id", (course_id,)).fetchall()
    enrolled = False
    if session.get("user_id"):
        enrolled = conn.execute("SELECT 1 FROM enrollments WHERE user_id=? AND course_id=?",
                                (session["user_id"], course_id)).fetchone() is not None
    conn.close()
    return render_template("course.html", course=course, lessons=lessons, enrolled=enrolled)

@app.route("/enroll/<int:course_id>", methods=["POST"])
@login_required
def enroll(course_id):
    conn = get_db()
    if not conn.execute("SELECT 1 FROM courses WHERE id=?", (course_id,)).fetchone():
        conn.close(); abort(404)
    try:
        conn.execute("INSERT INTO enrollments(user_id,course_id) VALUES(?,?)",
                     (session["user_id"], course_id))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()
    flash("You are enrolled in this course.", "success")
    return redirect(url_for("course_detail", course_id=course_id))

@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()
    courses = conn.execute("""
        SELECT c.*, e.enrolled_at,
        (SELECT COUNT(*) FROM lessons l WHERE l.course_id=c.id) AS total_lessons,
        (SELECT COUNT(*) FROM progress p JOIN lessons l2 ON l2.id=p.lesson_id
         WHERE p.user_id=? AND l2.course_id=c.id AND p.completed=1) AS completed_lessons
        FROM enrollments e JOIN courses c ON c.id=e.course_id
        WHERE e.user_id=? ORDER BY e.id DESC
    """, (session["user_id"], session["user_id"])).fetchall()
    results = conn.execute("""
        SELECT qr.*, q.title, c.title AS course_title
        FROM quiz_results qr JOIN quizzes q ON q.id=qr.quiz_id
        JOIN courses c ON c.id=q.course_id
        WHERE qr.user_id=? ORDER BY qr.id DESC LIMIT 10
    """, (session["user_id"],)).fetchall()
    conn.close()
    return render_template("dashboard.html", courses=courses, results=results)

@app.route("/learn/<int:course_id>")
@login_required
def learn(course_id):
    conn = get_db()
    course = conn.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
    if not course:
        conn.close(); abort(404)
    enrolled = conn.execute("SELECT 1 FROM enrollments WHERE user_id=? AND course_id=?",
                            (session["user_id"], course_id)).fetchone()
    if not enrolled and session.get("role") not in ("admin","instructor"):
        conn.close()
        flash("Please enroll in this course first.", "warning")
        return redirect(url_for("course_detail", course_id=course_id))
    lessons = conn.execute("""
        SELECT l.*, COALESCE(p.completed,0) AS completed
        FROM lessons l LEFT JOIN progress p ON p.lesson_id=l.id AND p.user_id=?
        WHERE l.course_id=? ORDER BY l.lesson_order,l.id
    """, (session["user_id"], course_id)).fetchall()
    quiz = conn.execute("SELECT * FROM quizzes WHERE course_id=? LIMIT 1", (course_id,)).fetchone()
    conn.close()
    return render_template("learn.html", course=course, lessons=lessons, quiz=quiz)

@app.route("/lesson/<int:lesson_id>/complete", methods=["POST"])
@login_required
def complete_lesson(lesson_id):
    conn = get_db()
    lesson = conn.execute("SELECT * FROM lessons WHERE id=?", (lesson_id,)).fetchone()
    if not lesson:
        conn.close(); abort(404)
    enrolled = conn.execute("SELECT 1 FROM enrollments WHERE user_id=? AND course_id=?",
                            (session["user_id"], lesson["course_id"])).fetchone()
    if not enrolled and session.get("role") not in ("admin","instructor"):
        conn.close(); abort(403)
    conn.execute("""INSERT INTO progress(user_id,lesson_id,completed,completed_at)
                    VALUES(?,?,1,CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id,lesson_id) DO UPDATE SET completed=1,completed_at=CURRENT_TIMESTAMP""",
                 (session["user_id"], lesson_id))
    conn.commit(); conn.close()
    return redirect(url_for("learn", course_id=lesson["course_id"]))

@app.route("/quiz/<int:quiz_id>", methods=["GET","POST"])
@login_required
def quiz(quiz_id):
    conn = get_db()
    quiz_row = conn.execute("""SELECT q.*, c.title AS course_title, c.id AS course_id
                               FROM quizzes q JOIN courses c ON c.id=q.course_id WHERE q.id=?""", (quiz_id,)).fetchone()
    if not quiz_row:
        conn.close(); abort(404)
    questions = conn.execute("SELECT * FROM questions WHERE quiz_id=? ORDER BY id", (quiz_id,)).fetchall()
    if request.method == "POST":
        score = 0
        for q in questions:
            if request.form.get(f"q{q['id']}","").lower() == q["answer"].lower():
                score += 1
        total = len(questions)
        conn.execute("INSERT INTO quiz_results(user_id,quiz_id,score,total) VALUES(?,?,?,?)",
                     (session["user_id"], quiz_id, score, total))
        conn.commit(); conn.close()
        return render_template("quiz_result.html", quiz=quiz_row, score=score, total=total)
    conn.close()
    return render_template("quiz.html", quiz=quiz_row, questions=questions)

@app.route("/admin")
@role_required("admin","instructor")
def admin():
    conn = get_db()
    if session["role"] == "admin":
        courses = conn.execute("""SELECT c.*, u.name instructor,
                                  (SELECT COUNT(*) FROM lessons l WHERE l.course_id=c.id) lesson_count
                                  FROM courses c LEFT JOIN users u ON u.id=c.instructor_id ORDER BY c.id DESC""").fetchall()
    else:
        courses = conn.execute("""SELECT c.*, u.name instructor,
                                  (SELECT COUNT(*) FROM lessons l WHERE l.course_id=c.id) lesson_count
                                  FROM courses c LEFT JOIN users u ON u.id=c.instructor_id
                                  WHERE c.instructor_id=? ORDER BY c.id DESC""", (session["user_id"],)).fetchall()
    users = conn.execute("SELECT id,name,email,role,created_at FROM users ORDER BY id DESC").fetchall() if session["role"]=="admin" else []
    conn.close()
    return render_template("admin.html", courses=courses, users=users)

@app.route("/admin/course/new", methods=["POST"])
@role_required("admin","instructor")
def create_course():
    title = request.form.get("title","").strip()
    description = request.form.get("description","").strip()
    category = request.form.get("category","General").strip()
    level = request.form.get("level","Beginner").strip()
    thumbnail = request.form.get("thumbnail","").strip()
    if not title or not description:
        flash("Title and description are required.", "danger")
        return redirect(url_for("admin"))
    instructor_id = session["user_id"]
    conn = get_db()
    cur = conn.execute("""INSERT INTO courses(title,description,category,level,thumbnail,instructor_id)
                          VALUES(?,?,?,?,?,?)""", (title,description,category,level,thumbnail,instructor_id))
    conn.commit(); cid = cur.lastrowid
    conn.close()
    flash("Course created successfully.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/course/<int:course_id>/lesson/new", methods=["POST"])
@role_required("admin","instructor")
def create_lesson(course_id):
    conn = get_db()
    course = conn.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
    if not course:
        conn.close(); abort(404)
    if session["role"]=="instructor" and course["instructor_id"] != session["user_id"]:
        conn.close(); abort(403)
    title = request.form.get("title","").strip()
    description = request.form.get("description","").strip()
    video_url = request.form.get("video_url","").strip()
    duration = request.form.get("duration","").strip()
    order_no = request.form.get("lesson_order","1").strip()
    try: order_no = int(order_no)
    except ValueError: order_no = 1
    if not title:
        flash("Lesson title is required.", "danger")
    else:
        conn.execute("""INSERT INTO lessons(course_id,title,description,video_url,duration,lesson_order)
                        VALUES(?,?,?,?,?,?)""", (course_id,title,description,video_url,duration,order_no))
        conn.commit()
        flash("Lesson added successfully.", "success")
    conn.close()
    return redirect(url_for("admin"))

@app.route("/admin/course/<int:course_id>/delete", methods=["POST"])
@role_required("admin")
def delete_course(course_id):
    conn = get_db()
    conn.execute("DELETE FROM courses WHERE id=?", (course_id,))
    conn.commit(); conn.close()
    flash("Course deleted.", "success")
    return redirect(url_for("admin"))

@app.route("/health")
def health():
    try:
        conn = get_db()
        conn.execute("SELECT 1").fetchone()
        conn.close()
        return jsonify(status="ok", database="sqlite")
    except Exception as exc:
        return jsonify(status="error", error=str(exc)), 500

@app.errorhandler(403)
def forbidden(_):
    return render_template("error.html", code=403, message="You do not have permission to access this page."), 403

@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", code=404, message="The requested page was not found."), 404

with app.app_context():
    init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
