# Step 11 — Similar Movies UI Simplification + Genre Search

## Changes

- Removed the visible **2 · Ready-made mode** section from the Similar Movies window.
- Removed the visible **3 · Optional filters** section from the Similar Movies window.
- Kept **1 · Choose similarity types** as the direct user control for explainable similarity.
- Added a **Genre** dropdown immediately beside the main movie search bar.
- Genre filtering works with title searches and can also be used on its own to browse the local CineSense catalogue by genre.
- Genre values are generated dynamically from the current catalogue rather than hard-coded, so new/imported genres appear automatically.
- Search results preserve the existing movie-detail workflow and TMDB catalogue expansion behavior.

The backend Similar Movies scoring remains intact; this step only simplifies the user-facing builder as requested.
