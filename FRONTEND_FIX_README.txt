CineSense AI — Blank Screen Fix

WHY THE PREVIOUS PAGE WAS BLACK
-------------------------------
Your logs prove the backend was already working:
- Uvicorn startup completed.
- /api/movies returned HTTP 200.
- /api/auth/me returned HTTP 401, which is expected before login.

The problem was therefore in the browser-side render path.

WHAT CHANGED
------------
1. Removed React StrictMode so development mode does not duplicate startup API calls.
2. Made the first render depend only on React/ReactDOM.
3. Added a visible Error Boundary. A JavaScript error now shows on screen instead of a black page.
4. Made API startup defensive and added a visible connection error panel.
5. Kept chat, comparison, planner, Responsible AI, authentication, consent, voice input,
   commercialisation screens, movie rows and hover cards.
6. Uses CSS transitions and React state for the stable initial UI.

HOW TO RUN
----------
Fresh download:
1. Extract ZIP.
2. Double-click start_windows.bat.
3. Keep the two command windows open.
4. Open http://127.0.0.1:5173
5. If Edge has the old page cached, press Ctrl+F5.
6. Click "Sign in" -> "Continue as demo".

If copying this over an older CineSense folder:
- Run repair_frontend_and_start.bat once.
