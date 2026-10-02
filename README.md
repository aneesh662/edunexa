# LearnHub - Flask + SQLite + GitHub + Render

Deployment-ready online tutorial application.

## Features
- Student registration and login
- Admin and instructor login
- Admin full user control: create, edit, password reset and delete students/instructors/admins
- Course creation and deletion
- Lesson creation
- YouTube lesson video links
- Google Drive PDF/resource links
- Course enrollment
- Student dashboard
- Lesson completion and progress
- Quizzes
- SQLite database
- Render health check

## Demo accounts
Admin: admin@example.com / admin123
Student: student@example.com / student123
Instructor: instructor@example.com / instructor123

## Local Windows setup
```bat
python -m venv venv
venv\\Scripts\\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000
Health: http://127.0.0.1:5000/health

## GitHub root
The repository root must directly contain app.py, requirements.txt, render.yaml, Procfile, templates/ and static/.

## Render
Runtime: Python
Build Command: `pip install -r requirements.txt`
Start Command: `gunicorn app:app`
Root Directory: blank if app.py is in repository root.

## YouTube
Paste a normal YouTube watch URL, youtu.be URL, or embed URL into the lesson's YouTube URL field. The learning page converts standard links into an embed player.

## Google Drive PDF
Upload the PDF to Google Drive, set the desired sharing permission (usually Viewer), copy the sharing link, and paste it into the lesson's Google Drive PDF link field. The PDF remains hosted by Google Drive.

## SQLite
SQLite is included as requested. For important production data, use persistent storage or migrate to PostgreSQL because an ephemeral deployment filesystem can lose local SQLite data on redeploy/restart.
