# Requirements Traceability Matrix

| Uploaded-plan requirement | Concrete implementation |
|---|---|
| 6 agents maximum | Six classes in `backend/app/agents/` |
| Orchestrator is only agent caller | `agents/orchestrator.py` |
| OpenAI-compatible chatbot | `services/llm.py` |
| Natural, detailed conversation | Orchestrator system style + detailed offline fallback |
| Last 5–10 turns of memory | Latest 10 encrypted `ChatTurn` records |
| NER / preference extraction | Mood agent extracts named phrases, genres and time expressions |
| Mood taxonomy | Happy, Relaxed, Sad/Cathartic, Thrilled, Romantic, Nostalgic |
| NLP summarisation use case | Curated seed blurbs are already condensed for comparison/UI grounding |
| Hybrid BM25 + semantic IR | `RetrievalRecommendationAgent` |
| Sentence embeddings option | sentence-transformers switch in `.env` |
| Free semantic fallback | TF-IDF/cosine similarity |
| Structured re-ranking | mood, genre, runtime, rating and history signals |
| Cold start | content/mood/genre signals when no watch history exists |
| Collaborative signal | watch-history genre/mood affinity |
| 2–4 movie comparison | `/api/compare` + Agent 4 |
| Grounded comparison | only database facts are provided to LLM |
| “Why this one” | comparison explanation always present |
| Movie plan scheduler | `/api/plan` + Agent 5 |
| Double feature | Scheduler tests movie pairs inside the time window |
| Suggested start time | finish-by minus chosen runtime |
| Guardian/security agent | prompt checks, output checks, safe traces |
| JWT | PyJWT in HttpOnly cookie |
| bcrypt/passlib | password hashing |
| Pydantic validation | all write request schemas |
| Encryption at rest | Fernet field-level encryption |
| Minimal chat retention | latest 10 turns and retention-days cleanup |
| Prompt injection defense | rule classifier + safe refusal |
| Output leakage defense | secret/prompt marker redaction |
| Agent communication protocol | `AgentEnvelope` |
| Traceability | `AgentTrace` table + Responsible-AI UI |
| Responsible-AI fairness | catalogue snapshot + repeated-studio diversification |
| Explainability | reasons, comparison table, trace IDs |
| Transparency | AI disclosure + detected mood chips |
| Human oversight | dismiss mood + flag recommendation |
| Netflix-style UI | cinematic dark interface and horizontal rows |
| Poster-driven cards | TMDB-ready poster URLs + designed offline poster fallbacks |
| Hover-preview card | animated overlay on movie cards |
| Persistent chat drawer | `ChatDrawer` |
| Smooth transitions | Framer Motion |
| Zustand | global client state |
| Recharts | comparison mood-fit chart |
| React + Vite + Tailwind | frontend stack |
| Python 3.11 + FastAPI | backend stack |
| SQLite / PostgreSQL | SQLAlchemy database abstraction |
| TMDB integration | admin metadata/poster sync endpoint |
| Manual mood tags | curated moods in `movies_seed.json` |
| Synthetic test set 50–100 | 64 cases in `evaluation_queries.json` |
| Free plan 10 AI queries/day | `AIUsage` quota |
| Premium saved plans | `SavedPlan` endpoint/UI |
| B2B API concept | protected `/api/b2b/recommend` |
| GitHub Actions | `.github/workflows/ci.yml` |
| Docker Compose | `docker-compose.yml` |

| Stateful conversational follow-ups | encrypted conversation state preserves last preferences/movie IDs for “shorter”, “compare first two”, and schedule follow-ups |
