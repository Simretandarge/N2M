# Next 251 Media (N2M)

A modern, premium, content-first media website built with **Django** and **Bootstrap 5**. Focus: Technology, AI, Startups, Innovation, Reviews — with an Africa + global angle.

---

## Environment & setup (what we use)

### Where the project lives

- **Project root:** `c:\Users\hp\Desktop\N2M\n2m_code\N2M` (or your clone path).
- Everything (code, virtual env, DB, media) lives under this folder.

### Python & virtual environment

- **Python:** 3.x (e.g. 3.11, 3.12, 3.13). The project was set up and run with Python 3.13.5 on Windows.
- **Virtual environment:** We use a **single venv** named **`.venv`** inside the project root. That keeps dependencies isolated from the rest of your system and makes “which environment” unambiguous: it’s always **this project’s `.venv`**.

### What “environment” means here

- **Environment** = the **Python interpreter + installed packages** you use to run Django and the app.
- We do **not** use Conda, pyenv, or a global Python for this project; we use the **`.venv`** in the repo folder.
- When you activate `.venv`, `python` and `pip` point to that venv, so `pip install` and `python manage.py` use the same environment.

### How to create the environment (first time)

From a terminal (PowerShell or Command Prompt):

```powershell
cd c:\Users\hp\Desktop\N2M\n2m_code\N2M

# Create the virtual environment (one time only)
python -m venv .venv

# Activate it (Windows)
.venv\Scripts\activate
```

On **macOS or Linux**:

```bash
cd /path/to/N2M
python3 -m venv .venv
source .venv/bin/activate
```

After activation you should see **`(.venv)`** at the start of your prompt. That means the environment is active.

### What’s installed in this environment

We install everything via **`requirements.txt`**:

- **Django** (4.2+ and below 5.1) — web framework, admin, auth, ORM.
- **Pillow** (10+) — image handling for `ImageField` (post/review images).

Django pulls in its own dependencies (e.g. `asgiref`, `sqlparse`, `tzdata`). No Node, no separate front-end build: the “front end” is Django templates + Bootstrap from a CDN.

### Project layout (high level)

- **`config/`** — Django project settings (`settings.py`), root `urls.py`, `wsgi.py`, `asgi.py`.
- **`content/`** — Main app: posts, reviews, categories, newsletter, views, admin.
- **`accounts/`** — Auth app: signup, sign in, logout, forgot password, profile.
- **`templates/`** — Base and app templates (e.g. `base.html`, `content/`, `accounts/`).
- **`static/`** — CSS (`theme.css`), images (logos, favicon).
- **`media/`** — Uploaded images (created when you upload; often in `.gitignore`).
- **`.venv/`** — Virtual environment (don’t commit; in `.gitignore`).
- **`db.sqlite3`** — SQLite database (dev only; don’t commit in production).
- **`manage.py`** — Django CLI (runserver, migrate, createsuperuser, etc.).

So: **“the environment we use”** = **Python 3.x + the `.venv` in this project, with Django and Pillow installed from `requirements.txt`.**

### How to run the app (after setup)

1. **Go to the project folder and activate the same environment:**
   ```powershell
   cd c:\Users\hp\Desktop\N2M\n2m_code\N2M
   .venv\Scripts\activate
   ```
2. **Install or refresh dependencies (if needed):**
   ```powershell
   pip install -r requirements.txt
   ```
3. **Apply migrations (if you haven’t or after pulling changes):**
   ```powershell
   python manage.py migrate
   ```
4. **Start the dev server:**
   ```powershell
   python manage.py runserver
   ```
5. Open **http://127.0.0.1:8000/** for the site and **http://127.0.0.1:8000/admin/** for the admin.

If you ever wonder “which environment did we use?” — it’s **this project’s `.venv`**, activated with `.venv\Scripts\activate` on Windows (or `source .venv/bin/activate` on macOS/Linux).

---

## Quick start (short version)

```powershell
cd c:\Users\hp\Desktop\N2M\n2m_code\N2M
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

- **Site:** http://127.0.0.1:8000/  
- **Admin:** http://127.0.0.1:8000/admin/  
- **Accounts:** http://127.0.0.1:8000/accounts/ (sign up, sign in, profile, forgot password)

## First-time setup

1. Create categories (e.g. **AI**, **Startups**) in Django admin so the AI and Startups hub pages have content.
2. Create and publish posts; toggle **Featured** and **Status** (draft/published) as needed.
3. Add reviews and newsletter signups via admin or the front-end forms.

## User roles (Admin, Editor, Writer)

Three roles control who can do what in the admin:

| Role   | Who                         | Posts & reviews                         | Categories & newsletter      |
|--------|-----------------------------|----------------------------------------|------------------------------|
| **Admin**  | Superuser (e.g. `createsuperuser`) | Full access; manage all content        | Full access                  |
| **Editor** | User in group **Editors**   | See all; publish, set featured, edit any | Add/edit/delete categories   |
| **Writer** | User in group **Writers**   | See only own; create drafts only       | View only; cannot add/edit   |

**How to assign roles**

1. In **Admin** go to **Authentication and authorization** → **Users**.
2. Create or edit a user; check **Staff status** so they can log in to admin.
3. Under **Groups**, add the user to **Writers** or **Editors** (or leave in no group for staff-only with no content permissions).
4. **Admin** = the superuser account; no group needed.

**Writer rules:** Writers see only their own articles/reviews, cannot set **Status** to Published or **Featured**, and cannot add/edit categories or newsletter subscribers. New articles/reviews are automatically set to their author.

## Tech stack

- **Backend:** Python, Django
- **Frontend:** Bootstrap 5, Django templates
- **Database:** SQLite (dev); switch to PostgreSQL in production
- **Static/Media:** Django staticfiles, ImageField (Pillow)

## Brand

- **Palette:** Primary Navy `#1F2A44`, Accent Green `#2F7D32`, Dark BG `#121826`, Silver text `#C7CBD6`, White `#FFFFFF`
- **Tone:** Calm, premium, authoritative, tech-forward
- **Logo:** Header uses circular icon + site name; favicon uses circular N2M icon

## Navigation (Phase 1)

Home | Articles | AI | Startups | Reviews | About | Contact

- **AI** and **Startups** are topic hubs (category pages). Create categories with slugs `ai` and `startups` for those links to show content.

## SEO

- Meta title/description on all pages
- OpenGraph tags on article/review detail pages
- `sitemap.xml` and `robots.txt` at `/sitemap.xml` and `/robots.txt`

## Future (not in MVP)

Reserved for later: Interviews, Podcast, Advertise/Sponsor pages, User accounts, Advanced editorial workflow.
