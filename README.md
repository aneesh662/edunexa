# LearnHub Online Tutorial Platform

Flask + SQLite + Bootstrap application. Public signup is disabled. Only administrators create student/instructor/admin accounts. Admins can create/edit/delete users, create/edit/delete courses, assign courses to individual students, and manage lessons with YouTube and Google Drive PDF links. Students can access only courses assigned to them.

## Render
Build: `pip install -r requirements.txt`
Start: `gunicorn app:app`

## Demo admin
Email: `admin@example.com`
Password: `admin123`

Change the default password after first login.
