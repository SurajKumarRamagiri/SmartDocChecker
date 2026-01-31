# SmartDocChecker

## 🚀 Overview
**SmartDocChecker (Frontend)** — Vite + React + TypeScript frontend for the SmartDocChecker project. This README documents how to set up, run, build, and debug the frontend locally and how to connect it to the backend and external services.

---

## 🛠 Prerequisites
- Node.js **LTS** (recommended: **18.x** or newer) — verify with `node -v`
- Package manager: **npm**, **pnpm**, or **yarn** — verify with `npm -v` or `pnpm -v` or `yarn -v`
- (Optional) A running backend API (the backend lives in `../backend` and typically runs with Uvicorn)

---

## 📦 Install dependencies
From the `frontend` folder run one of:

- npm: `npm install`
- pnpm: `pnpm install`
- yarn: `yarn`

---

## ⚙️ Environment variables
Vite exposes environment variables that are prefixed with `VITE_` to the client.
Common variables used by this project (example):

- `VITE_API_URL` — backend base URL (e.g., `http://localhost:8000`)
- `VITE_SUPABASE_URL` — Supabase project URL (if used)
- `VITE_SUPABASE_ANON_KEY` — Supabase anon/public key (if used)

Create a `.env.local` (or `.env`) in the `frontend` folder and add variables like:

```env
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=public-anon-key
```

> Note: Vite only exposes variables that start with `VITE_` to client code.

---

## 🧑‍💻 Development
Start the dev server with hot reload:

```bash
npm run dev
# or pnpm run dev
# or yarn dev
```

- Default dev server: `http://localhost:5173`
- To change the port: set `PORT` env var (or pass `--port` to `vite`).

If the app depends on the backend, start the backend from the project root:

```bash
cd ../backend
# using Uvicorn
uvicorn main:app --reload
```

---

## 📦 Production build & preview
Build the production bundle:

```bash
npm run build
```

Preview the built site locally (serves `dist`):

```bash
npm run preview
```

To deploy the build, serve the `dist` folder with any static server (NGINX, Cloud provider, or Node static server).

---

## ✅ Scripts
- `npm run dev` — start Vite dev server
- `npm run build` — build production assets
- `npm run preview` — locally preview production build
- `npm run lint` — run ESLint

---

## 🔧 Tools & Frameworks
- Vite (dev server and build)
- React + TypeScript
- Tailwind CSS (postcss)
- Supabase client (`@supabase/supabase-js`) for auth/storage (if used)

---

## 🐞 Troubleshooting
- Port conflict: Either stop the process using the port or change `PORT`.
- Environment changes not picked up: restart the dev server after changing `.env.local`.
- Node module issues: try `rm -rf node_modules package-lock.json && npm install` or `npm ci`.
- Linting: `npm run lint` and fix reported issues or configure ESLint rules in `package.json` / `.eslintrc`.

---

## 💡 Tips
- Use `pnpm` for faster installs if you prefer it.
- For Windows PowerShell set env vars like: `$env:VITE_API_URL = "http://localhost:8000"` or use a `.env` file.

---

## 📚 Where to look next
- Frontend source: `frontend/src/`
- Backend: `backend/`
- Vite config: `vite.config.ts`

---

If you want, I can also add a short troubleshooting script or example `.env.local` file to the repo. ✅