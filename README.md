# Online Tutorial Application

A clean Flask + SQLite + Bootstrap tutorial platform designed for GitHub and Render.

## Features

- Student registration/login
- Admin and instructor login
- Course catalogue and search
- Course enrollment
- Student dashboard
- Lesson learning page
- Mark lessons complete
- Quiz and scoring
- Admin/instructor course creation
- Lesson creation
- Admin course deletion
- SQLite database
- Health check endpoint
- Render deployment configuration
- Responsive Bootstrap UI

## Demo accounts

Admin:
- Email: admin@example.com
- Password: admin123

Student:
- Email: student@example.com
- Password: student123

Instructor:
- Email: instructor@example.com
- Password: instructor123

Change these passwords before production use.

## Run on Windows

Open Command Prompt in the project folder:

```bat
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

Open:
http://127.0.0.1:5000

Health check:
http://127.0.0.1:5000/health

## GitHub

The GitHub repository root must directly contain:

app.py
requirements.txt
render.yaml
Procfile
.gitignore
templates/
static/

Do NOT put these inside another `online_tutorial_flask/` folder when connecting the repository to Render.

## Render

Create a new Web Service from the GitHub repository.

Language:
Python 3

Build Command:
pip install -r requirements.txt

Start Command:
gunicorn app:app

Root Directory:
Leave blank when the files above are at repository root.

The included render.yaml can also be used as a Blueprint.

## SQLite note

SQLite is included because this project is intended for learning, prototypes and small deployments. For production with important data, use a persistent Render disk or migrate the database layer to PostgreSQL. Keep backups of your SQLite database.

## Important

Do not commit `.env` or secrets to GitHub.
