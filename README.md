# LearnHub Online Tutorial Platform

Flask + SQLite + Bootstrap application for an admin-controlled online tutorial platform. This release starts with an empty course/lesson catalog; content is created only through the application.

## Important account rule
There is **no public sign-up page**. Only an administrator can create students, instructors and administrators.

Default administrator:
- Email: `admin@example.com`
- Password: `admin123`

Change this password after deployment.

## Student course access
Students cannot self-enroll. The administrator assigns courses under each student's name. A student can access only assigned and published courses.

## Course management
Admin/instructor can create and edit courses. Course thumbnails can be selected directly from the computer as PNG/JPG/JPEG/WEBP/GIF (max 5 MB), or an image URL can be used.

## Lesson management
Admin/instructor can add, edit and delete lessons. Lesson editing supports:
- Lesson content
- YouTube video URL/path
- Google Drive PDF URL/path
- Duration
- Lesson order

## Student learning view
The learning page has a left lesson timeline. Students click a lesson to load only that lesson's video, PDF and content in the main area. Video playback keeps the normal playback timeline while disabling the full-screen/keyboard shortcuts and removing application-level share/download links. PDF material is embedded in the learning page. External providers may still expose their own controls, so browser-level copying, screenshots, screen recording, or provider-side downloads cannot be technically guaranteed to be impossible.

## Local setup
```bash
python -m venv venv
```
Windows:
```bash
venv\\Scripts\\activate
```
Then:
```bash
pip install -r requirements.txt
python app.py
```
Open `http://127.0.0.1:5000`.

## Render
Build command:
```text
pip install -r requirements.txt
```
Start command:
```text
gunicorn app:app
```

Health check:
```text
https://YOUR-APP.onrender.com/health
```

Expected response:
```json
{"status":"ok","database":"sqlite"}
```

## GitHub structure
Keep these directly in the repository root:
```text
app.py
requirements.txt
render.yaml
Procfile
templates/
static/
```

## SQLite note
SQLite is suitable for testing and small deployments. Render's normal filesystem is not persistent across all redeploy/restart scenarios. For production, move the database to PostgreSQL and use persistent object/file storage for uploaded thumbnails.


## SQLite database behavior

This project includes `tutorial.db` in the project root. The application creates it automatically only if the file is missing. On normal page refreshes, login, logout, or server restarts, the database is NOT reset, recreated, or reseeded. Data changes are made through the application routes only.

The admin can download the current database from **Manage → Download Database**. Keep `tutorial.db` in the GitHub repository if you want the same starting database to be deployed with the project. For Render, note that the local filesystem is not guaranteed to persist across every service replacement/redeploy; use persistent storage or PostgreSQL for production data.

## Student progress
Admins can open **Student Progress** and select any student. The page shows every assigned course, overall completion percentage, completed/total lessons, lesson-by-lesson status, media type and completion time. A **Progress** button is also available beside each student in User Management.

## No sample courses or lessons
The included `tutorial.db` contains only the administrator account. It contains **zero courses and zero lessons**. The application never seeds demo/sample courses or lessons on refresh or startup.
