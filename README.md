# NZ Chinese Golf Association CRM

[中文说明](README.zh-CN.md)

An integrated membership, event, and tournament CRM for the New Zealand Chinese Golf Association. It includes an admin dashboard, a member web app, and a FastAPI backend with bilingual (Chinese/English) support. V1.0 covers core association management; V1.5 extends the platform into a full golf tournament operations system (registration → grouping → scoring → review → ranking → handicap tracking).

## Live Demo

- Admin dashboard: _link pending deployment_
- Member app: _link pending deployment_

The backend runs on a free-tier host and may take ~30-60s to wake up on the first request after a period of inactivity. See [Demo Accounts](#demo-accounts) below to log in — the seed data includes both an **open tournament** (try the registration/eligibility flow) and a **completed tournament** with a published ranking (see grouping → scoring → review → ranking end-to-end without doing anything).

## Features

### V1.0 — Core CRM

| Module | Highlights |
|--------|------------|
| Auth & RBAC | JWT login, 6 roles, branch/team data scope |
| Organization | HQ → branch → team hierarchy, enrollment approval |
| Member CRM | Profiles, levels, blacklist, promotion rules, sleeping scan |
| Activities | Publish, register (incl. family), QR check-in, attendance |
| Finance | Ledger, reconcile, void/refund, member bills (no payment gateway) |
| Messages | In-app notifications: registration, dues reminders, activity alerts |

### V1.5 — Tournament Platform

| Module | Highlights |
|--------|------------|
| Competitions | Create/publish tournaments, registration with eligibility gating (blacklist, outstanding dues, handicap cap) |
| Grouping | Deterministic handicap-balanced grouping algorithm with team-clustering avoidance, tee-time scheduling, manual move/swap |
| Scoring | 18-hole digital scorecards, live gross/net calculation, draft → submit workflow |
| Review | Group peer confirmation → event director approval, reject-and-resubmit loop |
| Ranking | Individual (net score) and team (average net score) rankings, auto-awarded champion/runner-up/third, manual award override |
| Handicap | Audited manual adjustments with full history, trend dashboard (declining/rising/stable) |
| Courses | Course directory with holes/par/rating/slope |
| Sponsors | Sponsor CRM with contracts (amount, dates, benefits, optional competition link) |
| Analytics | Member/activity/competition/finance dashboard, branch-scoped for council admins |

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
| director | demo123456 | Event director | Admin |
| demo | demo123456 | Member | Member |

## Tests

```bash
cd backend
.venv\Scripts\activate
pytest -q    # 137 tests
```

> **Note:** the test suite runs against an in-memory SQLite database and is fully green (137/137). The full Alembic migration chain has also been verified end-to-end against a real PostgreSQL instance, including a full reseed of the English demo data.

## Roadmap

**V1.0 (Phases 0-7)** — complete: scaffold → auth → org → members → activities → finance → messages → integration demo.

**V1.5 (Phases 8-17)** — complete: competition CRUD & eligibility → grouping → scoring & review → ranking → handicap tracking → course directory → sponsor CRM → analytics dashboard → member home upgrade.

**Deferred to a later release:** cloud deployment, KMS/privacy compliance, WeChat mini-program, gender-based grouping, NZ Golf Handicap API integration, Stripe/PayPal payment gateway integration.

## License

Private / association use. Contact the repository owner for terms.
