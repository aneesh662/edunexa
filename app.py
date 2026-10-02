from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3, os, secrets
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "tutorial.db")
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
      password TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'student', created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS courses(
      id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT, category TEXT,
      level TEXT, thumbnail TEXT, instructor_id INTEGER, published INTEGER DEFAULT 1,
      created_at TEXT NOT NULL, FOREIGN KEY(instructor_id) REFERENCES users(id) ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS lessons(
      id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER NOT NULL, title TEXT NOT NULL,
      content TEXT, video_url TEXT, pdf_url TEXT DEFAULT '', duration INTEGER DEFAULT 0, position INTEGER DEFAULT 0,
      FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS enrollments(
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, course_id INTEGER NOT NULL,
      enrolled_at TEXT NOT NULL, UNIQUE(user_id,course_id),
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
      FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS course_assignments(
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, course_id INTEGER NOT NULL,
      assigned_at TEXT NOT NULL, UNIQUE(user_id,course_id),
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
      FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS progress(
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, lesson_id INTEGER NOT NULL,
      completed INTEGER DEFAULT 0, completed_at TEXT, UNIQUE(user_id,lesson_id),
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
      FOREIGN KEY(lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS quizzes(
      id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER NOT NULL, title TEXT NOT NULL,
      FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS questions(
      id INTEGER PRIMARY KEY AUTOINCREMENT, quiz_id INTEGER NOT NULL, question TEXT NOT NULL,
      option_a TEXT, option_b TEXT, option_c TEXT, option_d TEXT, answer TEXT NOT NULL,
      FOREIGN KEY(quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS quiz_results(
      id INTEGER PRIMARY KEY AUTOINCREMENT, quiz_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
      score INTEGER NOT NULL, total INTEGER NOT NULL, taken_at TEXT NOT NULL,
      FOREIGN KEY(quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(lessons)").fetchall()]
    if "pdf_url" not in cols:
        conn.execute("ALTER TABLE lessons ADD COLUMN pdf_url TEXT DEFAULT ''")
    # Seed only the administrator. All students/instructors must be created by an admin.
    if conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"] == 0:
        now = datetime.now().isoformat(timespec="seconds")
        conn.execute("INSERT INTO users(name,email,password,role,created_at) VALUES(?,?,?,?,?)",
                     ("Administrator","admin@example.com",generate_password_hash("admin123"),"admin",now))
    if conn.execute("SELECT COUNT(*) c FROM courses").fetchone()["c"] == 0:
        instructor = None
        now = datetime.now().isoformat(timespec="seconds")
        courses = [
            ("Python for Beginners","Learn Python from fundamentals to practical data handling.","Programming","Beginner","https://images.unsplash.com/photo-1526379095098-d400fd0bf935?w=800",instructor),
            ("Power BI Data Analytics","Build professional dashboards, KPIs and business reports.","Data Analytics","Intermediate","https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800",instructor),
            ("Advanced Excel","Master formulas, PivotTables, charts and data analysis.","Business","Intermediate","https://images.unsplash.com/photo-1611224923853-80b023f02d71?w=800",instructor),
            ("Financial Accounting","Understand accounting principles with practical business examples.","Finance","Beginner","https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=800",instructor)
        ]
        for c in courses:
            conn.execute("""INSERT INTO courses(title,description,category,level,thumbnail,instructor_id,created_at)
                            VALUES(?,?,?,?,?,?,?)""",(*c,now))
        rows = conn.execute("SELECT id,title FROM courses ORDER BY id").fetchall()
        lesson_data = {
            "Python for Beginners":[("Introduction to Python","Python is a readable, versatile programming language. In this lesson learn variables, types and the interpreter.",10),
                                    ("Variables and Data Types","Strings, numbers, lists, tuples and dictionaries with simple examples.",18),
                                    ("Conditions and Loops","Use if statements and loops to automate repeated work.",20),
                                    ("Functions and Mini Project","Create reusable functions and finish a small practical project.",25)],
            "Power BI Data Analytics":[("Power BI Overview","Understand the report workflow: import, transform, model and visualize.",12),
                                      ("Power Query Basics","Clean, merge and transform business data.",22),
                                      ("DAX Fundamentals","Create measures and calculated columns using DAX.",25),
                                      ("Dashboard Project","Build a management dashboard with KPIs and trends.",30)],
            "Advanced Excel":[("Excel Foundations","Tables, references, formatting and efficient workbook structure.",12),
                              ("Lookup and Logic","Use XLOOKUP, INDEX/MATCH and logical functions.",22),
                              ("PivotTables","Summarize large datasets and build useful reports.",25),
                              ("Dashboard Project","Combine formulas, pivots and charts into a dashboard.",30)],
            "Financial Accounting":[("Accounting Fundamentals","Understand the accounting equation and double-entry bookkeeping.",15),
                                    ("Journal and Ledger","Record transactions and post them to ledgers.",20),
                                    ("Trial Balance","Prepare and review a trial balance.",18),
                                    ("Financial Statements","Prepare income statement, balance sheet and cash flow basics.",25)]
        }
        for row in rows:
            pos=1
            for title,content,dur in lesson_data[row["title"]]:
                conn.execute("""INSERT INTO lessons(course_id,title,content,video_url,duration,position)
                                VALUES(?,?,?,?,?,?)""",(row["id"],title,content,"https://www.youtube.com/embed/dQw4w9WgXcQ",dur,pos))
                pos+=1
        # One quiz per course
        for row in rows:
            conn.execute("INSERT INTO quizzes(course_id,title) VALUES(?,?)",(row["id"],"Knowledge Check"))
            qid=conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            questions = [
                ("Which step normally comes first in a data workflow?","Import data","Delete database","Print report","Send email","A"),
                ("Which item helps track learning completion?","Progress","Wallpaper","Invoice","Folder","A"),
                ("What is a reusable block of Python code called?","Function","Cell","Slide","Record","A")
            ]
            for q in questions:
                conn.execute("""INSERT INTO questions(quiz_id,question,option_a,option_b,option_c,option_d,answer)
                                VALUES(?,?,?,?,?,?,?)""",(qid,*q))
    conn.commit(); conn.close()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper

def role_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if session.get("role") not in roles:
                flash("You do not have permission to access that page.","danger")
                return redirect(url_for("dashboard"))
            return fn(*args, **kwargs)
        return wrapper
    return deco

@app.context_processor
def globals():
    return {"current_user": session.get("name"), "current_user_id": session.get("user_id"), "role": session.get("role")}

@app.route("/")
def index():
    conn=db()
    if session.get("role") == "student":
        courses=conn.execute("""SELECT c.* FROM courses c
            JOIN course_assignments ca ON ca.course_id=c.id
            WHERE ca.user_id=? AND c.published=1 ORDER BY c.id DESC""",(session["user_id"],)).fetchall()
    else:
        courses=conn.execute("SELECT * FROM courses WHERE published=1 ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("index.html", courses=courses)

@app.route("/login", methods=["GET","POST"])

def login():
    if request.method=="POST":
        email=request.form["email"].strip().lower(); pw=request.form["password"]
        conn=db(); u=conn.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone(); conn.close()
        if u and check_password_hash(u["password"],pw):
            session.update(user_id=u["id"],name=u["name"],role=u["role"])
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("Invalid email or password.","danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    conn=db()
    if session.get("role") == "student":
        enrolled=conn.execute("""SELECT c.*, ca.assigned_at enrolled_at FROM courses c
            JOIN course_assignments ca ON ca.course_id=c.id
            WHERE ca.user_id=? AND c.published=1 ORDER BY ca.id DESC""",(session["user_id"],)).fetchall()
    else:
        enrolled=conn.execute("""SELECT c.*, e.enrolled_at FROM courses c JOIN enrollments e ON e.course_id=c.id
            WHERE e.user_id=? ORDER BY e.id DESC""",(session["user_id"],)).fetchall()
    stats={"courses":len(enrolled),"completed":conn.execute(
        "SELECT COUNT(*) c FROM progress WHERE user_id=? AND completed=1",(session["user_id"],)).fetchone()["c"]}
    conn.close()
    return render_template("dashboard.html",courses=enrolled,stats=stats)

@app.route("/courses")
def courses():
    q=request.args.get("q","").strip(); cat=request.args.get("category","").strip()
    conn=db()
    params=[]
    if session.get("role") == "student":
        sql="""SELECT c.* FROM courses c JOIN course_assignments ca ON ca.course_id=c.id
               WHERE ca.user_id=? AND c.published=1"""; params=[session["user_id"]]
    else:
        sql="SELECT * FROM courses WHERE published=1"
    if q: sql+=" AND (c.title LIKE ? OR c.description LIKE ?)" if session.get("role") == "student" else " AND (title LIKE ? OR description LIKE ?)"; params += [f"%{q}%",f"%{q}%"]
    if cat: sql+=(" AND c.category=?" if session.get("role") == "student" else " AND category=?"); params.append(cat)
    sql+=" ORDER BY id DESC"
    rows=conn.execute(sql,params).fetchall()
    cats=conn.execute("SELECT DISTINCT category FROM courses ORDER BY category").fetchall()
    conn.close()
    return render_template("courses.html",courses=rows,categories=cats,q=q,cat=cat)

@app.route("/course/<int:course_id>")
def course(course_id):
    conn=db()
    c=conn.execute("""SELECT c.*,u.name instructor FROM courses c LEFT JOIN users u ON u.id=c.instructor_id WHERE c.id=?""",(course_id,)).fetchone()
    lessons=conn.execute("SELECT * FROM lessons WHERE course_id=? ORDER BY position",(course_id,)).fetchall()
    quiz=conn.execute("SELECT * FROM quizzes WHERE course_id=? LIMIT 1",(course_id,)).fetchone()
    enrolled=False
    if session.get("user_id"):
        if session.get("role") == "student":
            enrolled=bool(conn.execute("SELECT 1 FROM course_assignments WHERE user_id=? AND course_id=?",
                                       (session["user_id"],course_id)).fetchone())
        else:
            enrolled=bool(conn.execute("SELECT 1 FROM enrollments WHERE user_id=? AND course_id=?",
                                       (session["user_id"],course_id)).fetchone())
    conn.close()
    if not c: return "Course not found",404
    return render_template("course.html",course=c,lessons=lessons,quiz=quiz,enrolled=enrolled)

@app.post("/course/<int:course_id>/enroll")
@login_required
def enroll(course_id):
    if session.get("role") == "student":
        flash("Courses are assigned by the administrator. You cannot self-enroll.","warning")
        return redirect(url_for("course",course_id=course_id))
    conn=db()
    conn.execute("INSERT OR IGNORE INTO enrollments(user_id,course_id,enrolled_at) VALUES(?,?,?)",
                 (session["user_id"],course_id,datetime.now().isoformat(timespec="seconds")))
    conn.commit(); conn.close()
    return redirect(url_for("course",course_id=course_id))

@app.route("/learn/<int:course_id>/<int:lesson_id>")
@login_required
def learn(course_id,lesson_id):
    conn=db()
    if session.get("role") == "student":
        allowed=conn.execute("SELECT 1 FROM course_assignments WHERE user_id=? AND course_id=?",(session["user_id"],course_id)).fetchone()
    else:
        allowed=conn.execute("SELECT 1 FROM enrollments WHERE user_id=? AND course_id=?",(session["user_id"],course_id)).fetchone()
    if not allowed:
        conn.close(); flash("This course has not been assigned to your account.","danger"); return redirect(url_for("dashboard"))
    c=conn.execute("SELECT * FROM courses WHERE id=?",(course_id,)).fetchone()
    lessons=conn.execute("SELECT l.*, COALESCE(p.completed,0) completed FROM lessons l LEFT JOIN progress p ON p.lesson_id=l.id AND p.user_id=? WHERE l.course_id=? ORDER BY l.position",(session["user_id"],course_id)).fetchall()
    lesson=conn.execute("SELECT * FROM lessons WHERE id=? AND course_id=?",(lesson_id,course_id)).fetchone()
    done={r["lesson_id"] for r in conn.execute("SELECT lesson_id FROM progress WHERE user_id=? AND completed=1",(session["user_id"],)).fetchall()}
    conn.close()
    if not lesson: return "Lesson not found",404
    return render_template("learn.html",course=c,lessons=lessons,lesson=lesson,done=done)

@app.post("/lesson/<int:lesson_id>/complete", endpoint="complete_lesson")
@login_required
def complete(lesson_id):
    conn=db(); l=conn.execute("SELECT * FROM lessons WHERE id=?",(lesson_id,)).fetchone()
    if l:
        conn.execute("""INSERT INTO progress(user_id,lesson_id,completed,completed_at) VALUES(?,?,1,?)
                        ON CONFLICT(user_id,lesson_id) DO UPDATE SET completed=1,completed_at=excluded.completed_at""",
                     (session["user_id"],lesson_id,datetime.now().isoformat(timespec="seconds")))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("dashboard"))

@app.route("/quiz/<int:quiz_id>", methods=["GET","POST"])
@login_required
def quiz(quiz_id):
    conn=db()
    qz=conn.execute("SELECT * FROM quizzes WHERE id=?",(quiz_id,)).fetchone()
    if not qz:
        conn.close(); return "Quiz not found",404
    if session.get("role") == "student" and not conn.execute("SELECT 1 FROM course_assignments WHERE user_id=? AND course_id=?",(session["user_id"],qz["course_id"])).fetchone():
        conn.close(); flash("This course has not been assigned to your account.","danger"); return redirect(url_for("dashboard"))
    qs=conn.execute("SELECT * FROM questions WHERE quiz_id=? ORDER BY id",(quiz_id,)).fetchall()
    if request.method=="POST":
        score=sum(1 for q in qs if request.form.get(str(q["id"]))==q["answer"])
        conn.execute("INSERT INTO quiz_results(quiz_id,user_id,score,total,taken_at) VALUES(?,?,?,?,?)",
                     (quiz_id,session["user_id"],score,len(qs),datetime.now().isoformat(timespec="seconds")))
        conn.commit(); conn.close()
        return render_template("quiz_result.html",score=score,total=len(qs),quiz=qz)
    conn.close()
    return render_template("quiz.html",quiz=qz,questions=qs)

@app.route("/admin")
@login_required
@role_required("admin","instructor")
def admin():
    conn=db()
    if session.get("role") == "admin":
        users=conn.execute("""SELECT u.id,u.name,u.email,u.role,u.created_at,
            (SELECT COUNT(*) FROM course_assignments ca WHERE ca.user_id=u.id) assigned_count
            FROM users u ORDER BY u.id DESC""").fetchall()
        courses=conn.execute("""SELECT c.*,u.name instructor,
            (SELECT COUNT(*) FROM lessons l WHERE l.course_id=c.id) lesson_count
            FROM courses c LEFT JOIN users u ON u.id=c.instructor_id ORDER BY c.id DESC""").fetchall()
    else:
        users=[]
        courses=conn.execute("""SELECT c.*,u.name instructor,
            (SELECT COUNT(*) FROM lessons l WHERE l.course_id=c.id) lesson_count
            FROM courses c LEFT JOIN users u ON u.id=c.instructor_id
            WHERE c.instructor_id=? ORDER BY c.id DESC""",(session["user_id"],)).fetchall()
    data={"users":conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"],
          "courses":conn.execute("SELECT COUNT(*) c FROM courses").fetchone()["c"],
          "lessons":conn.execute("SELECT COUNT(*) c FROM lessons").fetchone()["c"],
          "enrollments":conn.execute("SELECT COUNT(*) c FROM enrollments").fetchone()["c"]}
    assignments=[]
    if session.get("role") == "admin":
        assignments=conn.execute("""SELECT ca.user_id,ca.course_id,c.title,ca.assigned_at
            FROM course_assignments ca JOIN courses c ON c.id=ca.course_id ORDER BY ca.id DESC""").fetchall()
    conn.close()
    return render_template("admin.html",data=data,courses=courses,users=users,assignments=assignments)

@app.post("/admin/user/create")
@login_required
@role_required("admin")
def create_user():
    name=request.form.get("name","").strip(); email=request.form.get("email","").strip().lower(); pw=request.form.get("password","")
    role=request.form.get("role","student")
    if role not in ("student","instructor","admin"): role="student"
    if not name or not email or len(pw)<6:
        flash("Name, email and password (minimum 6 characters) are required.","danger"); return redirect(url_for("admin"))
    conn=db()
    try:
        conn.execute("INSERT INTO users(name,email,password,role,created_at) VALUES(?,?,?,?,?)",(name,email,generate_password_hash(pw),role,datetime.now().isoformat(timespec="seconds")))
        conn.commit(); flash("User created.","success")
    except sqlite3.IntegrityError: flash("Email already exists.","danger")
    finally: conn.close()
    return redirect(url_for("admin"))

@app.post("/admin/user/<int:user_id>/edit")
@login_required
@role_required("admin")
def edit_user(user_id):
    name=request.form.get("name","").strip(); email=request.form.get("email","").strip().lower(); role=request.form.get("role","student"); pw=request.form.get("password","")
    if role not in ("student","instructor","admin"): role="student"
    conn=db()
    try:
        if pw: conn.execute("UPDATE users SET name=?,email=?,role=?,password=? WHERE id=?",(name,email,role,generate_password_hash(pw),user_id))
        else: conn.execute("UPDATE users SET name=?,email=?,role=? WHERE id=?",(name,email,role,user_id))
        conn.commit(); flash("User updated.","success")
    except sqlite3.IntegrityError: flash("Email already exists.","danger")
    finally: conn.close()
    return redirect(url_for("admin"))

@app.post("/admin/user/<int:user_id>/delete")
@login_required
@role_required("admin")
def delete_user(user_id):
    if user_id==session.get("user_id"):
        flash("You cannot delete your own account.","warning"); return redirect(url_for("admin"))
    conn=db(); conn.execute("DELETE FROM users WHERE id=?",(user_id,)); conn.commit(); conn.close()
    flash("User deleted.","success"); return redirect(url_for("admin"))

@app.post("/admin/student/<int:user_id>/assign-course")
@login_required
@role_required("admin")
def assign_course(user_id):
    course_id=request.form.get("course_id","").strip()
    conn=db()
    user=conn.execute("SELECT id,role FROM users WHERE id=?",(user_id,)).fetchone()
    course=conn.execute("SELECT id FROM courses WHERE id=?",(course_id,)).fetchone() if course_id.isdigit() else None
    if not user or user["role"] != "student" or not course:
        conn.close(); flash("Select a valid student and course.","danger"); return redirect(url_for("admin"))
    conn.execute("INSERT OR IGNORE INTO course_assignments(user_id,course_id,assigned_at) VALUES(?,?,?)",(user_id,int(course_id),datetime.now().isoformat(timespec="seconds")))
    conn.commit(); conn.close(); flash("Course assigned to student.","success"); return redirect(url_for("admin"))

@app.post("/admin/student/<int:user_id>/remove-course/<int:course_id>")
@login_required
@role_required("admin")
def remove_course_assignment(user_id,course_id):
    conn=db(); conn.execute("DELETE FROM course_assignments WHERE user_id=? AND course_id=?",(user_id,course_id)); conn.commit(); conn.close()
    flash("Course assignment removed.","success"); return redirect(url_for("admin"))

@app.post("/admin/course/create")
@login_required
@role_required("admin","instructor")
def create_course():
    conn=db(); now=datetime.now().isoformat(timespec="seconds")
    conn.execute("""INSERT INTO courses(title,description,category,level,thumbnail,instructor_id,created_at)
                    VALUES(?,?,?,?,?,?,?)""",(request.form.get("title",""),request.form.get("description",""),request.form.get("category","General"),request.form.get("level","Beginner"),request.form.get("thumbnail",""),session["user_id"],now))
    conn.commit(); conn.close(); flash("Course created.","success"); return redirect(url_for("admin"))

@app.post("/admin/course/<int:course_id>/edit")
@login_required
@role_required("admin","instructor")
def edit_course(course_id):
    conn = db()
    course = conn.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
    if not course:
        conn.close()
        return "Course not found", 404
    if session.get("role") == "instructor" and course["instructor_id"] != session["user_id"]:
        conn.close()
        return "Forbidden", 403

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    category = request.form.get("category", "General").strip() or "General"
    level = request.form.get("level", "Beginner").strip() or "Beginner"
    thumbnail = request.form.get("thumbnail", "").strip()
    published = 1 if request.form.get("published") == "1" else 0

    if not title or not description:
        conn.close()
        flash("Course title and description are required.", "danger")
        return redirect(url_for("admin"))

    instructor_id = course["instructor_id"]
    if session.get("role") == "admin":
        raw_instructor = request.form.get("instructor_id", "").strip()
        if raw_instructor:
            try:
                candidate = int(raw_instructor)
                exists = conn.execute("SELECT id FROM users WHERE id=? AND role='instructor'", (candidate,)).fetchone()
                instructor_id = candidate if exists else None
            except ValueError:
                instructor_id = None
        else:
            instructor_id = None

    conn.execute(
        """UPDATE courses
           SET title=?, description=?, category=?, level=?, thumbnail=?, instructor_id=?, published=?
           WHERE id=?""",
        (title, description, category, level, thumbnail, instructor_id, published, course_id)
    )
    conn.commit()
    conn.close()
    flash("Course updated successfully.", "success")
    return redirect(url_for("admin"))

@app.post("/admin/course/<int:course_id>/lesson")
@login_required
@role_required("admin","instructor")
def create_lesson(course_id):
    conn=db(); course=conn.execute("SELECT * FROM courses WHERE id=?",(course_id,)).fetchone()
    if not course: conn.close(); return "Course not found",404
    if session.get("role")=="instructor" and course["instructor_id"]!=session["user_id"]:
        conn.close(); return "Forbidden",403
    pos=conn.execute("SELECT COALESCE(MAX(position),0)+1 p FROM lessons WHERE course_id=?",(course_id,)).fetchone()["p"]
    try:
        duration = int(request.form.get("duration", "0") or 0)
    except ValueError:
        duration = 0
    conn.execute("""INSERT INTO lessons(course_id,title,content,video_url,pdf_url,duration,position) VALUES(?,?,?,?,?,?,?)""",(course_id,request.form.get("title",""),request.form.get("content",request.form.get("description","")),request.form.get("video_url",""),request.form.get("pdf_url",""),duration,pos))
    conn.commit(); conn.close(); flash("Lesson added.","success"); return redirect(url_for("admin"))

@app.post("/admin/course/<int:course_id>/delete")
@login_required
@role_required("admin")
def delete_course(course_id):
    conn=db(); conn.execute("DELETE FROM courses WHERE id=?",(course_id,)); conn.commit(); conn.close(); flash("Course deleted.","success"); return redirect(url_for("admin"))

@app.route("/api/course/<int:course_id>/progress")
@login_required
def progress_api(course_id):
    conn=db()
    total=conn.execute("SELECT COUNT(*) c FROM lessons WHERE course_id=?",(course_id,)).fetchone()["c"]
    done=conn.execute("""SELECT COUNT(*) c FROM progress p JOIN lessons l ON l.id=p.lesson_id
                         WHERE p.user_id=? AND l.course_id=? AND p.completed=1""",(session["user_id"],course_id)).fetchone()["c"]
    conn.close(); return jsonify({"total":total,"completed":done,"percent":round(done/total*100) if total else 0})

@app.get("/health")
def health():
    try:
        conn=db()
        conn.execute("SELECT 1")
        conn.close()
        return {"status":"ok","database":"sqlite"}, 200
    except Exception as exc:
        app.logger.exception("Health check failed")
        return {"status":"error","message":str(exc)}, 500

init_db()

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)),debug=True)
