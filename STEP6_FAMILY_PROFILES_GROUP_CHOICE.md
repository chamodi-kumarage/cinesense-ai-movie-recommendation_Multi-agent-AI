# Step 6 — Family Profiles & Group Choice

This build completes the Family-plan workflow requested for CineSense AI while keeping the existing six-agent architecture.

## Implemented

1. Family profile CRUD with a five-profile maximum and account ownership checks.
2. Active-profile switching; recommendations, planner history, watched movies and ratings use the selected profile context.
3. `ProfilePreference` storage for preferred genres, disliked genres and preferred moods, plus encrypted per-profile watch/rating history.
4. Persistent `GroupSession` records containing the selected participant profile IDs, request, mood, available time and status.
5. Deterministic family consensus scoring per candidate movie: average member compatibility + satisfaction/balance bonus - conflict penalty.
6. Group recommendations created from Retrieval Agent candidates and re-ranked by the Family consensus layer.
7. Group comparison reuses the existing Comparison & Explainability Agent and augments its result with participant-specific consensus evidence.
8. `GroupVote` storage with one changeable vote per participating profile. Final score combines 65% group compatibility and 35% human vote share.

## Family APIs

- `GET /api/family/profiles`
- `POST /api/family/profiles`
- `PUT /api/family/profiles/{profile_id}`
- `DELETE /api/family/profiles/{profile_id}`
- `POST /api/family/profiles/switch`
- `GET /api/family/profiles/{profile_id}/preferences`
- `GET /api/family/profiles/{profile_id}/history`
- `POST /api/family/groups`
- `POST /api/family/groups/{session_id}/recommend`
- `GET /api/family/groups/{session_id}`
- `POST /api/family/groups/{session_id}/compare`
- `POST /api/family/groups/{session_id}/vote`
- `GET /api/family/groups/{session_id}/result`
- `POST /api/family/group-choice` (backwards-compatible create + recommend endpoint)

## Verification

- Python compilation: passed.
- Backend regression suite: 15/15 passed in the available test runtime. The sandbox did not contain the third-party `bcrypt` wheel, so verification used a temporary test-only bcrypt stub outside the project; the actual project still declares and uses real `bcrypt` through `backend/requirements.txt`.
- Frontend JSX/JavaScript syntax parse: passed with TypeScript `--noEmit --noResolve`.
- Archive contains the complete CineSense AI project, not only changed files.
