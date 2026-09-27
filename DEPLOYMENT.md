# Deployment Guide

This deploys the app on entirely free-tier infrastructure: [Neon](https://neon.tech) for Postgres, [Render](https://render.com) for the FastAPI backend, and [Vercel](https://vercel.com) for both React frontends. All three steps use the `WangliZhang77/GOLF` GitHub repo directly — no local build/upload needed.

Total cost: $0. The only real trade-off is Render's free web service spinning down after ~15 minutes of inactivity, so the first request after a while takes ~30-60s to wake up.

## 1. Database — Neon

Render's own free Postgres add-on auto-expires after 30 days, which defeats the point of a link you want to keep working on your resume. Neon's free tier doesn't expire.

1. Sign up at [neon.tech](https://neon.tech) (GitHub login is fine).
2. Create a new project (any name/region).
3. Copy the connection string it gives you — it looks like `postgresql://user:password@ep-xxxx.region.aws.neon.tech/dbname?sslmode=require`. Keep this for step 2 below.

## 2. Backend — Render

1. Sign up at [render.com](https://render.com) (GitHub login is fine) and connect the `WangliZhang77/GOLF` repository.
2. **New → Web Service**, pick the repo.
   - **Root Directory:** `backend`
   - **Environment:** Docker (it will pick up `backend/Dockerfile` automatically)
   - **Instance Type:** Free
3. Add these environment variables (Render dashboard → your service → Environment):
   | Key | Value |
   |---|---|
   | `DATABASE_URL` | paste Neon's connection string exactly as copied — the app auto-normalizes the `postgresql://` scheme |
   | `JWT_SECRET` | a fresh random value, e.g. run `openssl rand -hex 32` locally and paste the output — **never** the repo's default |
   | `APP_ENV` | `production` |
   | `DEBUG` | `false` |
4. Deploy. On boot, the container automatically runs `alembic upgrade head` then `python -m app.seed` before starting the server (see `backend/entrypoint.sh`) — no manual shell step needed, and it's safe to redeploy repeatedly since the seed data is idempotent.
5. Note the resulting URL, e.g. `https://golf-crm-backend.onrender.com`. Leave `CORS_ORIGINS` for step 4 below.

## 3. Frontends — Vercel

Import the repo **twice** as two separate projects (both auto-detect Vite: build command `npm run build`, output directory `dist`):

**Project 1 — admin dashboard**
- Root Directory: `admin-web`
- Environment variable: `VITE_API_BASE_URL` = `https://<your-render-url>/api`

**Project 2 — member app**
- Root Directory: `member-web`
- Environment variable: `VITE_API_BASE_URL` = `https://<your-render-url>/api` (same value)

Deploy both. You'll get two `*.vercel.app` URLs — note them down, you need each one for the other project in the next step.

## 4. Cross-link the two apps

Each login page has a "quick demo access" panel — a one-click "Continue as Admin/Member" button for its own app, and a button that jumps to the *other* app pre-authenticated. That cross-link needs to know the other app's URL:

- On the **admin-web** Vercel project, add `VITE_MEMBER_APP_URL` = the member app's `*.vercel.app` URL from step 3.
- On the **member-web** Vercel project, add `VITE_ADMIN_APP_URL` = the admin app's `*.vercel.app` URL from step 3.

Redeploy both (Vercel does this automatically when you save an env var).

## 5. Close the loop: CORS

Go back to Render → your backend service → Environment, and set:

```
CORS_ORIGINS=https://<your-admin>.vercel.app,https://<your-member>.vercel.app
```

Redeploy the backend (Render does this automatically when you save an env var change).

## 6. Smoke test

Open both Vercel URLs. Each login page has one-click "Continue as Admin" / "Continue as Member" buttons (no typing needed) plus a button that jumps to the other app already authenticated — try both directions. Or log in manually with the demo accounts from the README (`admin` / `director` / `demo`). Confirm:
- The admin dashboard's analytics sections render numbers (not blank — this confirms the backend + DB + CORS are all wired correctly).
- "Auckland Club Championship 2025" in Competitions shows a published ranking.
- The member app's home page shows Alex Chen's profile, handicap trend, and recent competition.

Once confirmed, send the two final URLs back so they can be filled into the README's Live Demo section.
