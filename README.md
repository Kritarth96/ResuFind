# Resufind

AI-assisted job discovery, built incrementally with Next.js + TypeScript and FastAPI.

## Run locally

Start the API in one terminal:

```powershell
cd api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Start the web app in another:

```powershell
cd web
npm run dev
```

Open `http://localhost:3000`, upload a PDF or DOCX resume, and review the extracted profile signal.

## Free deployment

Deploy `web/` to Vercel and `api/` to Render. The included `render.yaml` and `api/Dockerfile` provide the API configuration. On Vercel, set `NEXT_PUBLIC_API_URL` to the deployed Render URL. On Render, set `FRONTEND_URL` to the Vercel URL and add the provider keys as secrets.

The current SQLite database is suitable for local development only. Render's free filesystem is ephemeral, so move `storage.py` to PostgreSQL/Supabase before relying on saved jobs or alerts in production. Resume files are currently processed in memory and are not retained.