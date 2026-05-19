# Hosting Guide — Step by Step

This walks you through deploying the project so anyone can use it on the web.

**Architecture:** frontend on Vercel, backend on Railway. Both are linked by a public URL.

**Time:** about 45–60 minutes the first time.
**Cost:** free tiers cover testing. Real usage costs:
- Railway: ~$5/month for the small backend container + persistent disk
- Vercel: $0 (Hobby tier is enough)
- Anthropic API: pay-as-you-go (~$0.01–0.05 per PDF page extracted)

---

## Part 0 — What you need before you start

- [ ] A credit card (Railway and Anthropic require one; Vercel is free)
- [ ] An email address you can verify
- [ ] A web browser
- [ ] Roughly an hour

You do **not** need to install anything new on your computer.

---

## Part 1 — GitHub (15 min)

Both Railway and Vercel deploy directly from a GitHub repo. If you already have one with this code pushed, skip to Part 2.

### 1.1 Create a GitHub account

1. Go to https://github.com/signup
2. Enter email, create a password, pick a username.
3. Verify your email (check inbox).
4. Choose the **Free** plan when asked.

### 1.2 Create a new repository

1. Top-right **+** icon → **New repository**.
2. **Repository name:** `study-question-generator` (or anything you like).
3. **Public** or **Private** — Private is fine; Railway and Vercel can both read private repos after you authorize them.
4. **Do not** check "Add a README" (you already have one). Click **Create repository**.

GitHub now shows you a "quick setup" page with commands.

### 1.3 Push your code

Open a terminal in the project folder (`/Users/garden/Documents/test generator`) and run:

```bash
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/study-question-generator.git
git push -u origin main
```

(Replace `YOUR_USERNAME` with your GitHub username.)

When `git push` asks for a password, paste a **Personal Access Token**, not your GitHub password:
- GitHub → top-right avatar → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)** → **Generate new token (classic)**.
- Tick the **repo** scope. Click **Generate**, copy the token (you won't see it again), paste it as the password.

> **Verify `.env` did not get pushed.** Open your repo on GitHub, click into `backend/`, and confirm there is **no `.env` file**. There should be `.env.example` only. If `.env` is there, you must rotate the keys *and* remove the file from git history before going further.

---

## Part 2 — Rotate API keys (5 min)

The keys currently in `backend/.env` have been on disk and in chat logs. Rotate them before any public deployment.

### 2.1 Anthropic

1. Go to https://console.anthropic.com/login and sign in (or sign up if you haven't yet — you need a credit card to use the API).
2. Click **Settings** → **API Keys** in the left sidebar.
3. Find the existing key. Click the **⋯** menu → **Disable** or **Delete**.
4. Click **Create Key**. Name it `study-qgen-prod`. Copy the key (`sk-ant-…`) somewhere safe — you can't see it again.
5. **Settings → Billing**: confirm you have credits. Add $5–10 to start.

### 2.2 DeepSeek (optional, only if you use the DeepSeek model)

1. Go to https://platform.deepseek.com/sign_in and sign in.
2. **API Keys** in the left sidebar.
3. Delete the old key. Click **Create new API key**, copy it.

You'll paste these into Railway in Part 3.

---

## Part 3 — Backend on Railway (20 min)

Railway runs the FastAPI server with a persistent disk and `tectonic` for LaTeX.

### 3.1 Sign up for Railway

1. Go to https://railway.com/login.
2. Click **Login with GitHub**. Authorize Railway when GitHub asks.
3. **Settings → Billing**: add a credit card. The Hobby plan is $5/month and includes $5 of usage. Free trial gives ~$5 to start.

### 3.2 Add a Dockerfile to the backend

Railway needs to know how to build the backend with `tectonic` installed. Create `backend/Dockerfile` with this content:

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      tectonic ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data/uploads data/figures data/generated_exams

ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
```

> If `apt-get install tectonic` fails on Railway's build (Debian Bookworm sometimes lacks it), replace that line with:
> ```
> RUN apt-get update && apt-get install -y --no-install-recommends \
>       texlive-xetex texlive-latex-recommended texlive-fonts-recommended \
>       ca-certificates \
>     && rm -rf /var/lib/apt/lists/*
> ```
> This is heavier (~500 MB image) but always works.

Commit and push:

```bash
git add backend/Dockerfile
git commit -m "Add Dockerfile for Railway"
git push
```

### 3.3 Create the Railway project

1. Railway dashboard → **New Project** (top-right).
2. **Deploy from GitHub repo** → pick your `study-question-generator` repo.
3. Railway auto-detects the Dockerfile and starts building. Wait ~3–5 minutes for the first build.
4. **Important:** click the service → **Settings** tab → **Source** section → **Root Directory** → set to `backend`. Save. Railway redeploys.

### 3.4 Add a persistent volume

Without this, every redeploy wipes your uploaded PDFs and database.

1. Service → **Volumes** tab → **+ New Volume**.
2. **Mount path:** `/app/data`.
3. **Size:** 1 GB is plenty to start.
4. Save. Railway restarts the service.

### 3.5 Add environment variables

Service → **Variables** tab → click **+ New Variable** for each:

```
ANTHROPIC_API_KEY = sk-ant-...           (the rotated key from Part 2)
DEEPSEEK_API_KEY  = sk-...               (optional)
DEBUG             = false
DATABASE_URL      = sqlite:////app/data/study_questions.db
UPLOAD_DIR        = /app/data/uploads
FIGURE_DIR        = /app/data/figures
GENERATED_EXAM_DIR = /app/data/generated_exams
CORS_ORIGINS      = http://localhost:3000
```

> Leave `CORS_ORIGINS` as `http://localhost:3000` for now — you'll update it after Vercel gives you the frontend URL in Part 4.

Save. Railway redeploys.

### 3.6 Expose a public URL

1. Service → **Settings** tab → **Networking** section → **Generate Domain**.
2. Railway shows you a URL like `https://study-qgen-backend-production.up.railway.app`. Copy it.

### 3.7 Test the backend

Open a terminal and run:

```bash
curl https://YOUR-RAILWAY-URL.up.railway.app/health
```

You should see:
```json
{"status":"ok","app":"Study Question Generator"}
```

If you get an error: Railway service → **Deployments** tab → click the latest deploy → check **Build Logs** and **Deploy Logs**.

---

## Part 4 — Frontend on Vercel (10 min)

### 4.1 Sign up for Vercel

1. Go to https://vercel.com/signup.
2. Click **Continue with GitHub**. Authorize Vercel.
3. Pick the **Hobby (Free)** plan.

### 4.2 Update the Next.js config for the production backend

Edit `frontend/next.config.ts`. Add a `remotePatterns` entry for your Railway domain so figure images load:

```ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  devIndicators: false,
  images: {
    remotePatterns: [
      {
        protocol: "http",
        hostname: "localhost",
        port: "8000",
        pathname: "/api/assets/figures/**",
      },
      {
        protocol: "http",
        hostname: "127.0.0.1",
        port: "8000",
        pathname: "/api/assets/figures/**",
      },
      {
        protocol: "https",
        hostname: "YOUR-RAILWAY-URL.up.railway.app",
        pathname: "/api/assets/figures/**",
      },
    ],
  },
};

export default nextConfig;
```

Replace `YOUR-RAILWAY-URL.up.railway.app` with the actual hostname from Part 3.6 (no `https://`, no trailing slash). Commit and push:

```bash
git add frontend/next.config.ts
git commit -m "Allow Railway figures host in Next image"
git push
```

### 4.3 Import the project on Vercel

1. Vercel dashboard → **Add New…** → **Project**.
2. **Import Git Repository** — pick `study-question-generator`. (If you don't see it: **Adjust GitHub App Permissions** → grant Vercel access to that repo.)
3. **Framework Preset:** Next.js (auto-detected).
4. **Root Directory:** click **Edit** → select `frontend`. Critical step.
5. **Environment Variables** — click **Environment Variables** and add:

   ```
   NEXT_PUBLIC_API_URL = https://YOUR-RAILWAY-URL.up.railway.app
   ```

   (with `https://`, no trailing slash).

6. Click **Deploy**. Wait ~2–3 minutes.
7. When it finishes, Vercel gives you a URL like `https://study-question-generator.vercel.app`. Copy it.

### 4.4 Wire CORS back to Railway

1. Railway → your backend service → **Variables** tab.
2. Edit `CORS_ORIGINS`:

   ```
   CORS_ORIGINS = https://study-question-generator.vercel.app
   ```

   (use the Vercel URL from 4.3, no trailing slash). If you want preview deploys on Vercel to also work, comma-separate them:

   ```
   CORS_ORIGINS = https://study-question-generator.vercel.app,https://study-question-generator-git-main-yourname.vercel.app
   ```

3. Save. Railway redeploys.

---

## Part 5 — Sanity check (5 min)

1. Open the Vercel URL in your browser.
2. Upload a small PDF (1–3 pages is fine for the first test).
3. Click **Parse** → wait. The status should change to `parsed`.
4. Click **Extract** → wait. Status should change to `extracted`. This consumes Anthropic credits.
5. Open **Question Bank** → you should see questions.
6. **Study Set** → generate a random set, then **Download exam PDF**. If you get `No LaTeX engine found`, the Dockerfile didn't install `tectonic` — see the heavier `texlive-xetex` fallback in Part 3.2.

If you see `Failed to fetch` in the browser console:
- Open browser devtools → Network tab → click the failing request.
- If the error is **CORS**: the `CORS_ORIGINS` value on Railway doesn't match the Vercel URL exactly. Check for trailing slashes or http vs https.
- If the error is **404 / connection refused**: `NEXT_PUBLIC_API_URL` on Vercel is wrong, or Railway is down.

---

## Part 6 — Troubleshooting

| Symptom | Fix |
|---|---|
| Vercel build fails on `npm install` | Make sure **Root Directory = `frontend`** in Vercel project settings |
| Railway build fails on `pip install` | Make sure **Root Directory = `backend`** in the service settings |
| Railway build fails on `apt-get install tectonic` | Use the `texlive-xetex` fallback shown in Part 3.2 |
| Frontend loads but every request fails | Check `NEXT_PUBLIC_API_URL` on Vercel and `CORS_ORIGINS` on Railway — both must match exactly |
| Uploads disappear after a few hours | You skipped the volume in Part 3.4. Add it; old uploads from before are gone but new ones will persist |
| `Anthropic API credits exhausted` | Anthropic console → **Settings → Billing** → add credits |
| Figures don't render in the frontend | Step 4.2 — add the Railway hostname to `next.config.ts` `remotePatterns` |

---

## Part 7 — Going further (optional)

- **Custom domain.** Vercel → project → **Settings → Domains** → add your domain. Vercel handles HTTPS automatically. Update `CORS_ORIGINS` on Railway to match.
- **Auth.** The app currently has no login — anyone with the URL can upload PDFs and burn your Anthropic credits. To make it private, the simplest path is to put Vercel behind **Vercel Password Protection** (Pro plan) or add a shared secret header check in the backend.
- **Backups.** Railway volume snapshots aren't automatic on Hobby. Periodically `railway run sqlite3 /app/data/study_questions.db .dump > backup.sql` from your terminal.

---

## What to come back to me with

If you get stuck on any step, paste the exact error message and which Part/step you were on, and I can usually fix it in one round.
