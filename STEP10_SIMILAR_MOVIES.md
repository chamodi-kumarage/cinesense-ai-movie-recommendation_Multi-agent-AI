# Step 10 — Explainable Similar-Movie Discovery

This build adds a complete Similar Movies workflow while preserving the existing six-agent architecture.

## User flow

1. Open any movie card.
2. Click **Find Similar Movies**.
3. Choose one or more similarity types or a ready-made preset.
4. Optionally add a required genre, release-period rule, mood, or available-time limit.
5. CineSense returns ranked movies with the overall score, per-factor score breakdown, matching facts, and a grounded **Why similar?** explanation.
6. Add a result to the normal comparison shortlist or compare it directly with the original movie.

## Similarity factors

- **Cast** — leading actors receive more weight; shared cast is shown in the explanation.
- **Story / plot** — `overview + keywords + genres + moods` are encoded into semantic vectors and compared with cosine similarity. The standard backend is the existing 384-dimensional dense hash encoder. When optional Sentence Transformers are enabled, the configured model (default `all-MiniLM-L6-v2`) is used automatically.
- **Genre** — Jaccard overlap plus partial credit for related genre pairs such as Action/Adventure, Horror/Thriller, Romance/Drama, Science Fiction/Fantasy and Crime/Mystery.
- **Release period** — same year, ±3 years, ±5 years, same decade, or custom range.
- **Title** — normalized title tokens plus edit-distance similarity and franchise/shared-keyword boost. UI explanations explicitly warn that title similarity does not imply story similarity.
- **Director** — exact director match, ranked together with any other selected factors.
- **Studio** — exact production-studio match.
- **Producer** — verified TMDB producer / executive-producer / co-producer credits stored in a separate `movie_producers` table.
- **Mood** — source-movie mood overlap or an optional explicitly chosen target mood.

## Custom hybrid builder

Custom slider weights are normalized by the backend to 100% before scoring. Ready-made presets are also included:

- Similar Overall
- Story Most Important
- Same Cast and Creators
- Same Genre and Mood
- Same Era
- Something Different but Related
- Custom Combined Similarity

Selected factors remain authoritative; the preset only changes relative weights among those factors.

## Existing agents used

No seventh agent was introduced.

- **Orchestrator** coordinates `find_similar`.
- **Guardian** validates optional user filters and sanitizes every generated explanation.
- **Retrieval Agent** computes the similarity vectors, factor scores and ranking.
- **Comparison & Explainability Agent** converts grounded factor matches into readable explanations.
- **Mood & Preference Agent** handles an optional requested mood.
- **Scheduler Agent** validates an optional time window. When a time limit is supplied, over-length movies are excluded.

## Producer data

The uploaded 360-movie JSON does not contain a `producers` field, so CineSense does not fabricate producer names. Producer matching is backed by a separate normalized database table populated from verified TMDB credits. Newly imported TMDB movies save producer credits automatically. Administrators can also use **Admin → Overview → Enrich producer data** to enrich existing TMDB-linked catalogue movies in batches when `TMDB_API_KEY` is configured.

## API

`POST /api/similar`

Important request fields: `movie_id`, `modes`, `weights`, `preset`, `required_genre`, `year_mode`, custom year bounds, `mood`, `free_minutes`, and `limit`.

The response includes the original movie, ranked results, normalized weights, semantic backend, component scores, matching cast/genre/director/studio/producer facts, year difference, and the grounded `why_similar` explanation.

## Verification

- Python backend compilation: passed.
- Frontend JSX/JavaScript TypeScript parser check: passed.
- Step 9 comparison tests + Step 10 similarity tests: 8/8 passed.
- Full backend regression suite: 25/25 passed using a temporary test-only bcrypt compatibility module because the execution environment does not include the real `bcrypt` package. The packaged application still depends on the real bcrypt package declared by the project.
- Archive integrity check: performed after packaging.
