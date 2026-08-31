https://medical-web-l2z7np3xb5sznbvt2dz2q9.streamlit.app/

# MediGuide AI

An educational, safety-first symptom guidance prototype built with **LangChain** + **Streamlit** + **OpenAI**.

> ⚠️ **This is an educational prototype only.** It is not a medical device, does not provide diagnoses, and must never be used for real medical decisions. Always consult a licensed healthcare professional, and call emergency services for urgent situations.

## Features

- **Attractive login gate**: every visitor enters and verifies their own OpenAI API key before using the app — no key is baked into the deployment, so it's safe to host publicly
- Patient intake form (age, gender, symptoms, duration, severity, conditions, medications, notes)
- LangChain `ChatOpenAI` + `LLMChain` structured assessment returning strict JSON
- Streamed, human-readable narrative via `.stream()` + `st.write_stream`
- Urgency-level dashboard (LOW / MEDIUM / HIGH / EMERGENCY) with color-coded banners
- Switchable **InMemoryCache** / **SQLiteCache** to demonstrate LangChain caching
- Safe JSON parsing that never crashes the app on malformed model output
- Session history of past assessments (bonus feature)
- Multi-language guidance output

## Project structure

```
medical_ai_assistant/
├── app.py                 # Streamlit UI — run this
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── assets/                 # decorative images used on the login + main pages
└── src/
    ├── __init__.py
    ├── auth.py                # login page + API key verification
    ├── config.py           # settings + form options
    ├── prompts.py           # PromptTemplate + ChatPromptTemplate + JSON schema
    ├── chains.py             # ChatOpenAI, LLMChain, streaming
    ├── cache_manager.py       # in-memory + SQLite caching
    └── utils.py                # safe JSON parsing + helpers
```

## How the login works

On first load, the app shows a full-screen login page instead of the assessment
form. The visitor pastes their own OpenAI API key; clicking **"Verify & continue"**
makes a lightweight, no-cost call to OpenAI (`client.models.list()`) to confirm the
key is valid before letting them in. The key is kept only in that browser's
`st.session_state` for the duration of the session — it is never written to disk,
logged, or shared between users. A **Log out** button in the sidebar clears it.

This means:
- You do **not** need to put a real key in `.env` for a public deployment — `OPENAI_API_KEY` in `.env` is only a convenience fallback for local development.
- Each visitor pays for their own OpenAI usage with their own key.
- Restarting the browser tab / session requires logging in again (by design).

## Local setup

1. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure your API key**
   ```bash
   cp .env.example .env
   # then edit .env and paste your real OPENAI_API_KEY
   ```
   Get a key at https://platform.openai.com/api-keys. Never commit `.env`.

4. **Run the app**
   ```bash
   streamlit run app.py
   ```
   Streamlit will open at `http://localhost:8501`.

## Caching: InMemoryCache vs SQLiteCache

Both are registered globally via `set_llm_cache(...)` in `src/cache_manager.py`. Once
registered, LangChain automatically checks the cache — keyed on the exact prompt +
model + parameters — **before** making an API call. Submitting an identical form twice
will be visibly faster the second time.

| | InMemoryCache | SQLiteCache |
|---|---|---|
| Storage | RAM | `.cache/mediguide_cache.db` file on disk |
| Speed | Fastest | Fast, slightly slower than RAM |
| Survives app restart? | No | Yes |
| Best for | A single running session | Reuse across sessions/deployments |

Switch between them (or turn caching off) from the sidebar in the running app.

## Deployment

This app is ready to deploy as-is. Three common options:

### Option A — Streamlit Community Cloud (fastest, free)
1. Push this repository to GitHub (make sure `.env` is **not** committed — it's in `.gitignore`).
2. Go to https://share.streamlit.io, connect your GitHub repo, and set the main file to `app.py`.
3. In the app's **Secrets** settings, add:
   ```toml
   OPENAI_API_KEY = "sk-..."
   OPENAI_MODEL = "gpt-4o-mini"
   ```
4. Deploy. Streamlit Cloud installs `requirements.txt` automatically.

### Option B — Docker (any cloud VM / container platform)
Create a `Dockerfile` in the project root:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```
Then:
```bash
docker build -t mediguide-ai .
docker run -p 8501:8501 --env-file .env mediguide-ai
```

### Option C — Render / Railway / Fly.io
- Set the start command to: `streamlit run app.py --server.port=$PORT --server.address=0.0.0.0`
- Add `OPENAI_API_KEY` (and optional overrides) as environment variables in the platform's dashboard — do not upload `.env`.

## Testing scenarios

| # | Input | Expected behaviour |
|---|---|---|
| 1 | Age 25, runny nose + sore throat, 1-3 days, severity 2 | Urgency LOW; calm monitoring advice |
| 2 | Age 40, fever + cough, 4-7 days, severity 6 | Urgency MEDIUM/HIGH; advises seeing a professional |
| 3 | Severe chest pain + shortness of breath | Urgency HIGH/EMERGENCY; urges immediate help |
| 4 | Submit the same form twice (cache on) | Second run is faster; identical result |
| 5 | Empty symptoms | App warns the user and does not call the API |
| 6 | Language = Urdu | Guidance text returns in Urdu |

## Safety notes

- Disclaimers appear in the sidebar, main area, and results dashboard.
- The system prompt (`src/prompts.py`) hard-codes the rule that the model must never
  present a confirmed diagnosis, and must flag `EMERGENCY` urgency for dangerous symptoms.
- Malformed JSON from the model is caught and shown as a friendly error with the raw
  output available for debugging — it never crashes the app.

## License / disclaimer

Built for educational purposes as part of a LangChain + Streamlit coursework
assignment. Not a medical device. Not for real diagnosis or treatment.
