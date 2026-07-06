# NZ Chinese Golf Association CRM

[中文说明](README.zh-CN.md)

An integrated membership and event CRM for the New Zealand Chinese Golf Association (V1.0 Web product). It includes an admin dashboard, a member web app, and a FastAPI backend with bilingual (Chinese/English) support.

## Features (V1.0)

| Module | Highlights |
|--------|------------|
| Auth & RBAC | JWT login, 6 roles, branch/team data scope |
| Organization | HQ → branch → team hierarchy, enrollment approval |
| Member CRM | Profiles, levels, blacklist, promotion rules, sleeping scan |
| Activities | Publish, register (incl. family), QR check-in, attendance |
| Finance | Ledger, reconcile, void/refund, member bills (no payment gateway) |
| Messages | In-app notifications: registration, dues reminders, activity alerts |

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL
- **Admin:** React 18, TypeScript, Ant Design, react-i18next (`admin-web`, port **5173**)
- **Member:** React 18, TypeScript, antd-mobile, react-i18next (`member-web`, port **5174**)

## Project Structure

```text
golfststem/
  backend/          # FastAPI API
  admin-web/        # Admin dashboard
  member-web/       # Member web app
  scripts/          # start.ps1 / stop.ps1
  docs/             # Dev log & demo walkthrough
  docker-compose.yml
```

## Quick Start (Windows)

**Prerequisites:** Docker Desktop, Python 3.12+, Node.js 18+

```powershell
# One-click (opens 3 terminals: API + admin + member)
.\start.bat

# Or PowerShell
.\scripts\start.ps1

# Faster daily dev (skip seed & install checks)
.\scripts\start.ps1 -SkipSeed -SkipInstall
```

**Manual steps:**

```bash
docker compose up -d db
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

```bash
cd admin-web && npm install && npm run dev   # http://localhost:5173
cd member-web && npm install && npm run dev  # http://localhost:5174
```

- API docs: http://localhost:8000/docs
- Demo guide: [docs/演示走查.md](docs/演示走查.md)

## Demo Accounts

| Username | Password | Role | App |
|----------|----------|------|-----|
| admin | admin123456 | Super admin | Admin |
| finance | demo123456 | Finance officer | Admin |
| council | demo123456 | Council admin | Admin |
| captain | demo123456 | Team captain | Admin |
| demo | demo123456 | Member | Member |

## Tests

```bash
cd backend
.venv\Scripts\activate
pytest -q    # 50 tests
```

## Roadmap

Phases 0–7 are complete (scaffold → auth → org → members → activities → finance → messages → integration demo).

Deferred to V1.5+: cloud deployment, KMS/privacy compliance, WeChat mini-program, tournament scoring, Stripe/PayPal payments.

## License

Private / association use. Contact the repository owner for terms.
