# Step 9 — 360 Movie Catalogue + Advanced Comparison Lab

## Catalogue migration
- Replaced the original 36-title seed catalogue with the supplied 360-title JSON catalogue.
- Startup seeding is now an idempotent synchronisation instead of "seed only when empty".
- Existing installations are upgraded on the next backend startup: movies are matched by TMDB ID, then title + year, and missing titles are inserted.
- Existing admin-uploaded poster/backdrop URLs are preserved when the new seed has blank media URLs.
- `/api/movies` now supports returning up to 500 movies and defaults to the full 360-title local catalogue.

## Movie-card typography
- Poster and fallback cards now use the same 900-weight title styling so uploaded artwork no longer changes the visual weight of the movie name.

## Subscription completion
- Successful simulated subscription now displays a styled success pop-up with a thank-you message.
- The account plan refreshes before the pop-up appears.
- CineSense returns the user to the home page after the confirmation.

## Advanced comparison using the existing six-agent architecture
No new agent was introduced.
- Orchestrator coordinates the comparison flow and parses what-if conditions.
- Guardian validates free-text what-if input and sanitises the final explanation.
- Mood & Preference Agent resolves mood context.
- Retrieval & Recommendation Agent grounds the shortlist in catalogue records and personal history.
- Scheduler Agent contributes time-feasibility checks.
- Comparison & Explainability Agent applies mode-specific deterministic scoring and produces the grounded verdict.

### AI decision modes
- Best for My Mood
- Best Quality
- Shortest Option
- Most Exciting
- Safest Group Choice
- Something Different

### What-if simulator
Supports conditions such as:
- `What if I only have 90 minutes?`
- `What if I want something less intense?`
- `What if rating matters more than mood?`
- `What if we remove horror?`

The same shortlist is rescored and rank movement is returned to the UI.

### Pairwise tournament
- Presents two shortlisted films at a time.
- Records the user's reason for choosing the winner.
- Eliminates the loser and advances the winner.
- Continues until one film remains.
- Preference-oriented reasons update the active profile's existing `ProfilePreference` record; no seventh agent or separate preference engine is created.

### Regret / decision risk
Each comparison row receives a Low / Medium / High risk level derived from:
- runtime conflict,
- disliked genres,
- mood mismatch,
- language mismatch,
- pace / intensity mismatch.

### Comparison visualisations
The frontend now includes:
1. Overall suitability bar chart
2. Six-axis multi-criteria radar chart
3. Runtime comparison chart with fit/tight/exceeds states
4. Mood compatibility chart
5. Rating versus mood-fit scatter plot with runtime-sized bubbles

## Verification completed
- Supplied catalogue parsed successfully: 360 records.
- 360 unique TMDB IDs and 360 unique title/year pairs.
- Every supplied record contains the expected movie fields.
- Backend Python source compiles successfully with `compileall`.
- Frontend JSX/JavaScript parses successfully with TypeScript `--allowJs --jsx preserve`.
- Advanced comparison scoring was smoke-tested across all six decision modes and what-if/risk conditions.
- Full backend regression suite completed: **21/21 tests passed**. The container does not ship the real `bcrypt` package, so the validation run used a temporary test-only bcrypt compatibility shim; the packaged project still requires and uses real `bcrypt>=4.3,<5` in normal installation.
