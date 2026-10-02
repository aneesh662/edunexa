# Online Tutorial Application — Flask + SQLite

A responsive learning platform with:
- Student registration/login
- Instructor/admin login
- Course library and search/filter
- Course enrollment
- Video lesson player
- Lesson completion and progress tracking
- Quizzes and results
- Admin/instructor course creation
- Lesson creation
- SQLite database
- Render deployment configuration

## Run locally

```bash
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open: http://127.0.0.1:5000

## Demo accounts

Admin:
admin@example.com / admin123

Student:
student@example.com / student123

Instructor:
instructor@example.com / instructor123

Change these passwords before production use.

## SQLite database

The database is automatically created as `tutorial.db` in the project root after the first run.

## GitHub + Render

1. Create a GitHub repository.
2. Upload all project files.
3. On Render choose New > Web Service.
4. Connect the GitHub repository.
5. Build command: `pip install -r requirements.txt`
6. Start command: `gunicorn app:app`
7. Add `SECRET_KEY` as a secret environment variable.

### Important production note

SQLite is excellent for learning, demos and small deployments. On Render, the normal web-service filesystem is not persistent across all redeploy/restart scenarios. For production student data, migrate the database to PostgreSQL and store uploaded media in object storage.
