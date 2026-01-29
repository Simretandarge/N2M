# Next 251 Media (N2M)

A modern, premium, content-first media website built with **Django** and **Bootstrap 5**. Focus: Technology, AI, Startups, Innovation, Reviews — with an Africa + global angle.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

- **Site:** http://127.0.0.1:8000/  
- **Admin:** http://127.0.0.1:8000/admin/

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

**Writer rules:** Writers see only their own posts/reviews, cannot set **Status** to Published or **Featured**, and cannot add/edit categories or newsletter subscribers. New posts/reviews are automatically set to their author.

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
