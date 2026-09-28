# Resufind API

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The API exposes `POST /api/resumes/parse` for PDF and DOCX uploads and `POST /api/jobs/search` for ranked results. Jobs use a provider interface in `providers.py`: local fixtures always work, while SerpAPI is enabled when `SERPAPI_KEY` is set.

```powershell
$env:SERPAPI_KEY = "your-key"
uvicorn main:app --reload --port 8000
```

Alternatively, create `api/.env` with `SERPAPI_KEY=your-key`. To enable Gemini resume enrichment, add `GEMINI_API_KEY=your-key` and optionally `GEMINI_MODEL=gemini-3.8-flash`. OpenAI remains supported as a fallback with `OPENAI_API_KEY=your-key`. Keep that file private and do not commit it.

Gemini is tried first, OpenAI second, and local parsing last. Without an AI key, parsing remains local and deterministic. If an AI provider is unavailable or returns invalid data, the API keeps the local profile rather than failing the upload.

Providers are isolated so additional official APIs or compliant aggregators can be added without changing profile scoring. Each provider failure is returned in `source_status`; the remaining sources still produce results.