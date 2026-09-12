# CineSense AI

CineSense AI is a six-agent, mood-aware movie discovery and viewing companion built for IT3041. The current package keeps the original hub-and-spoke FastAPI architecture while completing the main gaps identified in the updated current-system document.

## Implemented system

- Six bounded agents coordinated only by the Conversational Orchestrator.
- MCP-inspired trace envelope with privacy-safe logging.
- OpenAI and Groq live-LLM adapters plus a full offline fallback.
- Enhanced rule NLP plus optional spaCy NER; mood, genre, runtime, dislikes and entities remain available even without optional NLP packages.
- Hybrid pure-Python BM25 + semantic hash-vector retrieval, with optional Sentence Transformers.
- Grounded comparison/explainability and mood/time scheduling.
- Dynamic plot-summary endpoint using the configured LLM with a deterministic fallback.
- JWT HttpOnly-cookie authentication, bcrypt, Fernet encryption, consent and hardened Guardian input/output checks.
- Encrypted profile-specific watch ratings; recommendation history follows the active Family profile.
- Visible frontend Logout control that clears the session and UI state.
- Family plan backend/frontend: up to five profiles, switching, separate watch histories and multi-profile group recommendations.
- Stripe-ready Premium/Family checkout, signed webhook handling, automatic `user.plan` updates, renewal/status tracking, cancellation and failed-payment state.
- B2B client key creation (stored hashed), per-key monthly usage counters, 10,000-call starter allowance and $6/1,000-call overage estimation.
- TMDB enrichment **and catalogue expansion** for popular movies when an API key is configured.
- Production monitoring events, PostgreSQL production compose, HTTPS deployment guidance and legal-policy drafts.
- Responsible-AI fairness snapshot, human mood correction, recommendation flagging and grounded LLM context.

## Quick start

1. Install Python 3.11+ and Node.js 20+.
2. Copy `backend/.env.example` to `backend/.env`.
3. Run `start_windows.bat` on Windows or `./start_mac_linux.sh` on macOS/Linux.
4. Open `http://localhost:5173`.

The demo account remains available through **Continue as demo** (`demo@cinesense.ai`, password `Demo123!`).

## Live LLM

Offline mode works without secrets. To demonstrate the assignment's live LLM requirement, configure either:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_real_key
OPENAI_MODEL=gpt-4o-mini
```

or:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=your_real_key
GROQ_MODEL=llama-3.3-70b-versatile
```

No secret keys are included in this ZIP.

## Optional spaCy NER

Install `backend/requirements-nlp-optional.txt`, install the `en_core_web_sm` model, then set `ENABLE_SPACY_NER=true`. If spaCy is unavailable, CineSense automatically uses the improved dependency-free extractor.

## TMDB catalogue expansion

Configure `TMDB_API_KEY` and `ADMIN_API_KEY`, then call:

```bash
curl -X POST "http://localhost:8000/api/admin/sync-tmdb?expand=true&pages=2" -H "X-Admin-Key: your_admin_key"
```

This enriches existing TMDB-linked records and adds new popular titles not already present.

## Stripe subscriptions

Set `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PREMIUM_PRICE_ID`, `STRIPE_FAMILY_PRICE_ID`, and `PUBLIC_APP_URL`. The billing modal can then create real checkout sessions. Stripe webhooks are the source of truth for activating, changing or cancelling `user.plan`.

## B2B

The legacy `B2B_API_KEY` still works. Production-like per-client keys can be created with `POST /api/admin/b2b-clients` using `X-Admin-Key`; the plaintext key is shown once and only its SHA-256 hash is stored. `/api/b2b/recommend` increments monthly usage and `/api/b2b/usage` returns included calls and estimated overage.

## Production

See `docs/PRODUCTION_DEPLOYMENT.md`, `docker-compose.prod.yml`, and `docs/legal/`. PostgreSQL is supported through `DATABASE_URL`; HTTPS should be terminated by the deployment platform/reverse proxy. Production cookies are marked Secure automatically.

## Testing note

`backend/tests/` contains the original smoke/regression tests plus tests for the newly completed security, logout, Family, encrypted watch-history and B2B features. Run with `pytest -q` after installing `backend/requirements.txt`. Frontend validation is `npm run build` after `npm install`.

## 2026 UX and university-project billing refresh

The current build includes a polished catalogue experience with a searchable movie index, click-through movie details, a larger conversational assistant, user-facing Responsible AI explanations, and a simulated subscription workflow designed for demonstrations without a real payment gateway.

### Simulated subscriptions

Open **Plans**, click Premium or Family, then choose **Subscribe**. The billing form validates an exactly 16-digit Luhn-valid card number. A safe test value is `4242 4242 4242 4242`. The backend never stores the full card number or CVV: it stores only masked card metadata plus encrypted billing-profile fields. Subscription status is persisted and updates the existing plan-gated features.

### Search and movie details

The home page search supports title, year, language, director, studio, genre, and mood terms. Selecting any search result or catalogue card opens a user-facing movie detail modal. Internal agent traces and backend metadata are intentionally not shown in the normal user experience.

## Smart Mood & Time Watch Planner (Step 5)

The planner has been expanded into a personalised planning workspace rather than a simple runtime form.

- **Smart Mood Check-In:** emoji mood controls plus free-text mood analysis. The detected mood can always be confirmed or corrected by the user.
- **Quick Planner:** 30, 60, 90, 120, 180 and 240 minute shortcuts immediately run the planner using the confirmed mood and genre. If no full catalogue movie genuinely fits a short window, CineSense says so instead of inventing a result.
- **Finish-Time + Buffer Planning:** accepts normal wording such as `I need to sleep by 11:30 PM`, supports a configurable wind-down buffer, and returns suggested start, movie finish, requested finish time and spare time.
- **Adaptive explanations:** `Why this plan fits you` combines the current mood, requested runtime, genre and recent viewing preferences while remaining grounded in catalogue facts.
- **Mood History & Personal Insights:** recent planner activity is stored per active profile and used to produce simple weekday/mood/genre patterns.
- **Weekly Mood & Watch Summary:** watched-title count, watch time, most common mood, favourite genre and average runtime are calculated from the active profile's recent activity.
- **Calendar-aware planning:** the built-in CineSense Calendar works without third-party credentials. Users can add busy times, find free evening windows, and turn a selected window directly into a watch plan.
- **Google Calendar (optional):** OAuth read/write integration is available when deployment credentials are configured. It can read free/busy availability and add watch-plan events.
- **Add to Calendar:** generated plans can be added to the connected calendar and an `.ics` file is produced for standard calendar applications. Reminder time is configurable in the UI.

### Optional Google Calendar configuration

Add these values to `backend/.env`:

```env
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/api/calendar/google/callback
```

In Google Cloud, enable the Google Calendar API and register the exact redirect URI above (or the production equivalent). If these values are left empty, the built-in CineSense Calendar remains fully usable for local demos and university evaluation.

## Step 7: Admin, movie media, trailer hero and expanded catalogue
The latest build includes a seeded administrator dashboard, secure movie poster/backdrop uploads, YouTube hero-trailer selection, broad on-demand TMDB search/import and an administrator security assessment dashboard. See `STEP7_ADMIN_MEDIA_SECURITY.md`.

Development administrator credentials are `admin@cinesense.ai` / `CineSenseAdmin!2026`. Change both `ADMIN_PASSWORD` and `SECRET_KEY` before production; production startup refuses the default values.

To search/import a much wider real-world movie catalogue, create a TMDB API key and put `TMDB_API_KEY=...` in `backend/.env`. CineSense searches local data first, imports missing TMDB matches on demand, and lets an admin bulk-import popular titles.

## Explainable Similar Movies (Step 10)
Open any movie and choose **Find Similar Movies** to rank the catalogue by story semantics, genres, cast, era, title patterns, director, studio, verified producers and mood. Users can combine factors, change normalized weights, apply genre/year/mood/time filters, inspect the full score breakdown, and send any result into the existing comparison shortlist. Producer matching uses verified TMDB credits in `movie_producers` rather than guessing from studio metadata.
