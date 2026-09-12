# Step 7 — Admin, Cinematic Media, Expanded Catalogue & Security

## Administrator account
A seeded administrator account is created on first start:
- Email: `admin@cinesense.ai`
- Password: `CineSenseAdmin!2026`

These values are configurable with `ADMIN_EMAIL` and `ADMIN_PASSWORD`. Production startup refuses to run with the default admin password or default application `SECRET_KEY`.

## Admin dashboard
Authenticated administrators receive an **Admin** navigation item. The dashboard provides:
- system overview (users, movies, profiles, uploads, TMDB status),
- catalogue/movie media management,
- poster and backdrop uploads,
- YouTube trailer attachment and featured-home-trailer selection,
- user/account overview,
- Responsible AI/security assessment and recent security events,
- TMDB popular-movie bulk import when a TMDB key is configured.

Uploads accept JPG/PNG/WebP only, enforce a size limit, validate file signatures, generate server-side random names and never trust the client filename.

## Cinematic UI
The home hero can play the administrator-selected YouTube trailer as a muted looping cinematic background. A dark readability overlay preserves contrast without making the trailer almost invisible. Movie cards use uploaded/TMDB posters. Movie detail, catalogue, modal and admin surfaces were given stronger depth, imagery and cinematic styling.

## Large catalogue strategy
A small local seed cannot realistically contain every film users may search. CineSense now uses a scalable hybrid approach:
1. Search the local catalogue first.
2. If there are too few matches and `TMDB_API_KEY` is configured, query TMDB Search.
3. Import validated results into CineSense and return them immediately.
4. Administrators can bulk-import popular TMDB pages from the Admin dashboard.
5. Imported items carry `source: tmdb`; seed titles carry `source: curated`.

Set `TMDB_API_KEY` in `backend/.env` to enable broad global title discovery.

## Security and Responsible AI controls
Implemented/verified controls cover the requested assessment areas:
- Prompt injection, jailbreak, prompt leakage, instruction override and manipulation detection before LLM execution.
- Output secret/PII redaction and unsafe-output filtering.
- bcrypt password hashing, HttpOnly session cookies, SameSite policy, Secure cookies in production, failed-login lockout and server-side admin authorization.
- Encrypted chat/profile/billing-sensitive fields and masked card storage.
- Restricted CORS, request-size checks, security headers, HSTS in production, upload validation and typed FastAPI request validation.
- Admin-only internal traces; internal agent metadata remains hidden from normal users.
- Grounded catalogue context, fairness snapshot, explainability, feedback/user control and security regression tests.
- Retrieval provenance, local-first retrieval, validated TMDB imports and query length/sanitization.

The Admin Security tab runs prompt-attack regression cases and reports the status of the main security controls. HTTPS/TLS still has to be terminated by the production reverse proxy/platform, as described in `docs/PRODUCTION_DEPLOYMENT.md`.

## Subscription UX
After a simulated Premium or Family subscription is activated, CineSense displays a success alert, refreshes the account plan, closes billing and returns the user to the home page.

## Verification
- Python source compile check: passed.
- Frontend JSX/JavaScript parse check with TypeScript compiler: passed.
- Backend regression suite: **17 tests passed** using a local bcrypt compatibility stub in the constrained build environment.
- Added tests cover seeded admin access, admin security assessment, media upload, featured trailer configuration and public hero metadata.
