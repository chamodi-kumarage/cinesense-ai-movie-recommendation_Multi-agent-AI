CineSense AI — CORS + bcrypt Fix

WHY THE SCREEN SHOWED "FAILED TO FETCH"
---------------------------------------
The backend itself was healthy, but the browser sent:

OPTIONS /api/movies -> 400
OPTIONS /api/auth/me -> 400

That means the CORS preflight request was rejected.

The frontend was opened at:
http://127.0.0.1:5173

The previous backend only allowed:
http://localhost:5173

Although both point to your own PC, browsers treat them as different origins.

WHAT IS FIXED
-------------
1. Backend now permits BOTH:
   - http://127.0.0.1:5173
   - http://localhost:5173

2. Frontend automatically uses the same hostname for the API:
   - frontend 127.0.0.1 -> backend 127.0.0.1
   - frontend localhost -> backend localhost

3. Passlib was removed from password hashing.
   CineSense now uses bcrypt directly, removing the:
   "module 'bcrypt' has no attribute '__about__'"
   warning on Python 3.14.

4. Existing standard bcrypt password hashes remain compatible.

HOW TO RUN
----------
1. Close all previous CineSense backend/frontend command windows.
2. Extract this ZIP into a NEW folder.
3. Double-click start_windows.bat.
4. Keep Backend and Frontend windows open.
5. Open:
   http://127.0.0.1:5173
6. Press Ctrl+F5 once if the browser had an older CineSense page open.
7. Click Sign in -> Continue as demo.

EXPECTED BACKEND LOG
--------------------
OPTIONS /api/movies -> 200 OK
GET /api/movies -> 200 OK

A 401 for GET /api/auth/me before signing in is normal.
