# CineSense AI: Full Generative AI Video Script

**Video length:** about 10 minutes  
**Frame:** 16:9, 1920×1080, 24 or 30 fps  
**Audience:** beginners, classmates, and evaluators  
**Style:** friendly product demonstration with clear diagrams and real screen recordings

## Before recording

Use real CineSense screen recordings for all claims about the application. Use GenAI for the opening/closing visuals, narration if desired, music, captions, and abstract diagrams. Do not ask a video generator to invent UI, movie scores, recommendation results, or system behavior. Record those directly from the running app.

Use a demo or synthetic account and fictional preference text. Hide notifications, personal browser tabs, credentials, API keys, private messages, and billing details. If an optional integration is unavailable, describe it as optional rather than presenting a mock result as live.

The system has six agents: Conversational Orchestrator, Guardian, Mood & Preference Analysis, Retrieval & Recommendation, Comparison & Explainability, and Mood & Time Scheduler. OpenAI/Groq are optional LLM providers, not extra agents. The message envelope is MCP-inspired; call it an agent message/trace envelope, not a full MCP implementation. Subscription UI includes a simulated university-demo mode; live Stripe, TMDB, Google Calendar, and hosted LLM functions need configuration.

---

## Complete scene-by-scene script

### Scene 1 — The problem: too many choices (0:00–0:25)

**Visual:** Show an evening movie watcher scrolling through a crowded streaming screen, hesitating, then looking frustrated. Cut to the CineSense home page.

**Voice-over:** “Have you ever spent more time choosing a movie than watching one? CineSense AI helps narrow down the choices. Tell it what kind of mood you’re in, what you enjoy, or how much time you have—and it helps you find a movie that fits.”

**On-screen title:** `CineSense AI` / `A smarter way to choose a movie`

**GenAI video prompt:** “Create a 7-second cinematic, realistic video of a young adult at home in the evening, scrolling through a crowded movie streaming interface and feeling indecisive. Warm home lighting, natural acting, gentle camera push-in, tasteful modern room, no readable words, no logos, no recognizable movie posters. End with a smooth dark-blue transition. 16:9 landscape.”

**Edit:** Keep this generated shot brief. Add title text in the editor for clean typography.

### Scene 2 — Meet CineSense (0:25–0:55)

**Visual:** Real screen recording of the homepage. Slowly show the hero text, chat button, watch planner, search bar, movie rows, and navigation.

**Voice-over:** “CineSense is an AI-based movie discovery and viewing companion. You can browse the catalogue, search for a title, talk to the recommendation assistant, compare movies, find similar movies, and plan your movie time. The same system connects these features through a team of six specialised agents.”

**On-screen callouts:** `Discover` · `Ask` · `Compare` · `Find similar` · `Plan`

**GenAI motion prompt:** “Create an elegant software explainer transition: five simple icons—movie catalogue, chat bubble, comparison scales, connected movie cards, and clock—move toward a central CineSense-style glow. Deep navy background with teal and amber accents, clean lines, no readable labels, no logos, 16:9.”

### Scene 3 — Explain the six-agent architecture (0:55–1:55)

**Visual:** Show a labeled diagram. The Orchestrator is the central hub, with five specialist agents around it. Animate request and result arrows. Add labels in post-production.

**Voice-over:** “Here is how the multi-agent system is organised. The Conversational Orchestrator is the coordinator. It interprets the request type and sends work to the right specialist. The Guardian checks user input and the final response. Mood and Preference Analysis extracts signals such as mood, genre, disliked genres, movie names, and available minutes. Retrieval and Recommendation finds and ranks catalogue candidates. Comparison and Explainability scores alternatives and describes why they fit. Mood and Time Scheduler builds a plan that fits a time window. The Orchestrator brings the result back into one response.”

**On-screen diagram labels:**

- **1. Conversational Orchestrator:** interprets intent and coordinates agent calls
- **2. Security & Responsible-AI Guardian:** checks input and output
- **3. Mood & Preference Analysis:** extracts structured preferences
- **4. Retrieval & Recommendation:** searches and ranks candidates
- **5. Comparison & Explainability:** compares scores and reasons
- **6. Mood & Time Scheduler:** fits movie choices into a watch window

**GenAI diagram prompt:** “Generate a clean animated hub-and-spoke diagram for a software presentation. The center node is Conversational Orchestrator. Exactly five surrounding nodes are Guardian, Mood & Preference Analysis, Retrieval & Recommendation, Comparison & Explainability, and Mood & Time Scheduler. Show a request moving from user through the center to relevant agents and a result returning through the center. Professional flat motion design, no extra agents, no gibberish text; labels will be added in editing. 16:9.”

**Presenter note:** State that not every request uses every specialist. The Orchestrator chooses the path based on whether the user asks for recommendations, a comparison, or a schedule.

### Scene 4 — Full end-to-end recommendation demo (1:55–3:15)

**Visual:** Open the real CineSense chat. Enter: `I’m exhausted, need something funny, and only have 90 minutes.` Show the response and resulting movie cards. Pause on the title, runtime, rating, and reason. If the catalogue has no fitting result, show the actual response and loosen one condition on-screen.

**Voice-over:** “Let’s follow a request from start to finish. I’ll say: ‘I’m exhausted, need something funny, and only have 90 minutes.’ The Guardian inspects the message. Mood and Preference Analysis identifies a relaxed mood, comedy preference, and 90-minute limit. The Orchestrator gives those signals to Retrieval. Retrieval searches the catalogue and ranks suitable candidates. The system uses BM25 text matching and semantic hash-vector similarity; Sentence Transformers can be enabled as an optional retrieval component. The recommendation is grounded in catalogue details such as genre, runtime, rating, and description. The assistant then explains why the matches fit.”

**Screen annotations:** `Natural-language request` → `Mood, genre, time` → `Hybrid catalogue retrieval` → `Ranked, explained choices`

**GenAI overlay prompt:** “Create a minimal transparent-style animation for overlay on a real application screen: a speech bubble turns into three tags—mood, genre, available time—passes through a shield icon, then searches a grid of blank movie cards and returns three blank result cards. No movie titles, ratings, artwork, or invented results. Navy, teal, amber, clean motion, 16:9.”

**Optional detail card:** “Mood and entity extraction uses enhanced rules; spaCy NER is optional. Live OpenAI/Groq LLM response generation is optional; offline deterministic fallback is available.”

### Scene 5 — Catalogue browsing, search, and movie details (3:15–4:00)

**Visual:** Use the search bar to find a movie. Show catalogue results and open a detail view with overview, year, runtime, genres, rating, cast, and available media. Show mood-based movie rows on the homepage.

**Voice-over:** “CineSense also works as a regular movie catalogue. Search by title and supported metadata, browse mood-based rows, and open a movie to see its details. Catalogue facts make it easier to understand what a recommendation refers to. An administrator can enrich or expand the catalogue through TMDB when the required key is configured; the local seeded catalogue works without it.”

**On-screen callouts:** `Search` · `Movie details` · `Mood collections` · `Optional TMDB catalogue expansion`

**GenAI transition prompt:** “Create a short transition of abstract movie tiles rearranging into a clean searchable catalogue grid, then one card expands into a detail panel. Use fictional unbranded artwork and blank interface text areas; do not imitate a real streaming brand. Sophisticated product motion graphics, 16:9.”

### Scene 6 — Find similar movies (4:00–4:45)

**Visual:** Open a movie and select Find Similar Movies. Show real similar-movie results, selected similarity factors, and the explanation text. If available in the demo, adjust a factor or filter and show how the order changes.

**Voice-over:** “If you already have a movie in mind, Find Similar Movies creates another path through the catalogue. Similarity can consider story themes, genres, cast, release year, title pattern, director, studio, verified producer credits, and mood. The interface can show the score breakdown and a plain-language reason, such as shared themes or cast. You can adjust factors and filters, then add a result to the comparison shortlist.”

**On-screen note:** `Similarity scores describe selected catalogue signals; they are not a promise of personal preference.`

**GenAI visual prompt:** “Animate two fictional blank movie cards connected by small visual tags representing story, genre, cast, year, director, and mood. Then show a ranked stack of blank cards. No names, logos, film posters, or numerical scores. Minimal dark-background product animation, 16:9.”

### Scene 7 — Compare choices with explanations (4:45–5:35)

**Visual:** Select two to four movies for the shortlist and open Compare. Demonstrate at least two available modes. Show score dimensions and a grounded explanation. If the scenario controls are present, change a condition such as time or intensity and show the ranking update.

**Voice-over:** “When I have a shortlist, Comparison and Explainability helps me choose. It can rank for best mood fit, best quality, shortest option, most exciting, safest group choice, or something different. Under the hood, it considers mood, genre, runtime fit, rating, pace, and history signals using mode-specific weights. The comparison returns a ranking and explanation, and can show how a changed scenario affects the order. These scores are guidance based on the chosen criteria.”

**GenAI motion prompt:** “Create a simple explainer animation with three blank movie cards flowing into a six-column score display: mood, genre, time, rating, pace, history. A mode selector changes emphasis and the cards reorder. Leave all numbers and movie details blank for the real product recording. Clear, restrained, professional, 16:9.”

### Scene 8 — Mood check-in and smart watch planner (5:35–6:30)

**Visual:** Open Watch Planner. Demonstrate mood selection/correction, genre selection, a quick time option, or a natural-language finish-by request. Show actual single-film or double-feature output, remaining minutes, and buffer. Show insights or weekly summary if available.

**Voice-over:** “The Watch Planner brings mood and time together. I can choose or correct a mood, set genres, use a quick runtime option, or enter a finish-by time with a wind-down buffer. The Scheduler checks what fits and selects a single film or a double feature where appropriate. The planner can also summarize recent profile activity, mood patterns, watch time, and genre preferences. It reports when nothing fits rather than inventing a movie.”

**On-screen formula:** `Available time − buffer = movie time`

**GenAI video prompt:** “Create a clean timeline animation for an evening movie plan. Show a movie block ending before a finish-by marker, with a separate wind-down buffer after it. Use blank labels for post-production, deep navy with amber and teal highlights, simple clock and film icons, 16:9.”

### Scene 9 — Calendar planning (6:30–7:00)

**Visual:** Show local CineSense Calendar busy slots, free-window results, and add-plan/export if available. If Google Calendar is connected in the demo environment, show the real connected flow; otherwise do not show a fake connection.

**Voice-over:** “Calendar support helps find a free evening window and turn it into a watch plan. The built-in CineSense Calendar can be used locally. Google Calendar connection and event creation are optional and require deployment credentials. Plans can also be added to compatible calendar applications through an ICS file when that flow is available.”

**GenAI motion prompt:** “Animate a generic weekly calendar with busy blocks and one highlighted free evening window. A movie plan card fits into that window, leaving time for a buffer. No real names, email addresses, dates, or Google branding. Clean, accessible software illustration, 16:9.”

### Scene 10 — Family profiles and group choice (7:00–7:45)

**Visual:** Open Family. Show up to five profiles, create or switch a synthetic profile, display preferences/history, and launch a group-choice workflow. Show group shortlist, compare, voting, and final result if practical in the recording.

**Voice-over:** “Family features support up to five profiles with separate preference settings and watch histories. For a shared movie night, members can contribute their preferences to Group Choice. CineSense builds a consensus shortlist, lets the group compare candidates and vote, then presents a final selection. This makes the recommendation flow useful for a household, not only one viewer.”

**GenAI visual prompt:** “Create an abstract family movie-choice animation with four diverse profile icons contributing mood and genre tokens to a shared shortlist. Show simple votes converging on one blank movie card. No personal data, names, or real movie posters. Friendly, inclusive, professional, 16:9.”

### Scene 11 — User controls and responsible-AI features (7:45–8:20)

**Visual:** Show the Responsible AI screen: explanations, user correction of mood, flag recommendation, fairness/catalogue snapshot. Show sign-in/demo and logout briefly, with safe synthetic credentials hidden.

**Voice-over:** “The interface includes user-facing responsible-AI features. Viewers can correct a detected mood, inspect why a recommendation was made, and flag a recommendation that feels wrong. The catalogue diversity snapshot gives context about the movies available. Account features include registration, login, demo access, consent gating for AI actions, and logout. The Guardian performs input checks and output filtering as part of the request flow.”

**On-screen text:** `Understand the reason` · `Correct your preferences` · `Flag a mismatch`

**GenAI visual prompt:** “Create a clean visual explainer of a user reviewing a recommendation, opening a ‘why this fits’ panel, adjusting a mood control, and flagging a mismatch. Use generic interface elements with blank text, no personal details. Human-centered, calm, accessible, 16:9.”

### Scene 12 — Plans, administrator tools, and B2B (8:20–9:00)

**Visual:** Quickly show plans page and simulated billing disclosure. Then show administrator overview, catalogue search/import/media settings/security assessment, and B2B usage if these are enabled. Mask every key and user detail.

**Voice-over:** “The project also includes plan and operations features. The plans page explains Free, Premium, Family, and a B2B concept. Subscription status can be demonstrated in simulated project mode; real Stripe checkout and webhook updates require configuration. Admin tools support catalogue management, media uploads, featured trailer settings, user overview, security events, and assessment checks. The B2B API supports client-key management, recommendation requests, and monthly usage reporting. TMDB, Stripe, live LLM providers, and other external services only operate when configured.”

**On-screen labels:** `Demo subscription flow` · `Admin catalogue and media` · `B2B usage metering` · `External services: configuration required`

**GenAI transition prompt:** “Create a polished abstract montage of software operations: catalogue tiles being updated, a poster image placeholder uploading, a security shield dashboard, and a usage meter. No real keys, user data, provider logos, or invented numbers. Keep it brief and visually consistent with a navy-teal product demo, 16:9.”

### Scene 13 — Technical stack and data flow (9:00–9:35)

**Visual:** Diagram: React/Vite browser → FastAPI API → Orchestrator → specialist agents; database below; optional external providers shown dashed. Animate a metadata envelope with trace ID, sender, receiver, intent, and safe summary labels; no real request content.

**Voice-over:** “Technically, the frontend uses React and Vite, and the backend uses FastAPI. The API passes agentic requests through the Orchestrator. Agent handoffs use a structured trace envelope with a trace ID, sender, receiver, intent, payload, and timestamp. The project uses SQLAlchemy with SQLite by default and supports PostgreSQL through configuration. Optional LLM and external-service connections are configured separately. This architecture lets the interface offer several experiences while keeping the agent responsibilities clear.”

**GenAI diagram prompt:** “Create an accurate software architecture animation: React/Vite client connects to FastAPI; FastAPI routes agentic work to one central Conversational Orchestrator; exactly five specialist agent nodes connect through the Orchestrator; database labeled SQLite/PostgreSQL; optional provider nodes are dashed and marked optional. Animate a trace envelope containing metadata fields only, payload shown blank. Do not add components or extra agents. Labels added in post. 16:9.”

### Scene 14 — Summary and closing (9:35–10:00)

**Visual:** Return to the homepage and show a satisfying real recommendation result. End card with project name, course/group attribution, and optional team names.

**Voice-over:** “CineSense brings movie discovery, personalised recommendations, similarity search, comparison, family choice, and watch planning into one multi-agent application. Its agents each have a clear role, and its explanations help viewers understand the recommendations. That is CineSense AI: discover a movie, understand why it fits, and enjoy your movie night. Thank you for watching.”

**On-screen end card:** `CineSense AI` / `Discover · Understand · Decide`

**GenAI closing prompt:** “Create a 6-second elegant closing video: a quiet home cinema scene with a few abstract movie cards softly coming into focus, warm amber and deep blue light, gentle camera drift, no logos, no readable text, no recognizable film posters. Fade into a clean dark end-card background. 16:9 landscape.”

---

## Detailed six-agent spotlight scenes

Use these as six extra scenes after the architecture overview, or replace the short agent explanations in Scene 3 with this sequence. Together they add about 4–5 minutes. The UI does not expose every internal agent message to an ordinary viewer, so record the real app for inputs and results, then add clearly labeled explanatory overlays for the internal flow. Do not present invented trace payloads or fabricated intermediate outputs as live logs.

### Agent Scene 1 — Conversational Orchestrator (about 0:45)

**Purpose:** Explain how the system decides what kind of task the user asked for and coordinates the specialists.

**What to show:** Start with a real chat input such as `I feel tense. Find a mystery under 120 minutes.` Add a diagram overlay: User → Guardian input check → Orchestrator → Mood/Preference → Retrieval → Guardian output check → User. Then show the actual assistant result. In a second overlay card, show the other intent branches: “compare these movies” routes to Comparison; “plan a movie night / finish by 11” routes to Scheduler. Do not imply one recommendation request invokes every agent.

**Narration:** “The Conversational Orchestrator is the traffic controller for CineSense’s agent workflow. When a request arrives, it creates a trace ID, asks the Guardian to inspect the input, and classifies the request as a recommendation, comparison, or schedule. It then calls the relevant specialist with a structured agent envelope containing the sender, receiver, intent, and task payload. For a recommendation, it asks Mood and Preference Analysis to structure the request and Retrieval to find candidates. For a comparison, it routes the selected movies and criteria to Comparison and Explainability. For a viewing plan, it routes candidates and time constraints to the Scheduler. Before the response is returned, the Guardian checks the output. The Orchestrator also maintains conversation context for follow-up turns.”

**Technical details to show in small text:** `ConversationalOrchestratorAgent`; `_intent()` identifies compare/schedule/recommend; `_env()` builds `AgentEnvelope`; `chat()` coordinates the agent calls; trace ID follows the workflow. Agent traces are an internal diagnostic mechanism, not proof that every internal step is visible in the UI.

**GenAI video prompt:** “Create a 10-second clean software animation of a central coordinator routing three different request cards. A ‘recommend’ request branches to mood analysis and retrieval; a ‘compare’ request branches to comparison; a ‘watch plan’ request branches to scheduling. All branches return to the coordinator and pass through a shield icon before reaching the user. Show exactly one central coordinator and the named specialist roles only. No fake logs, no invented data, no unreadable text; labels will be added in post. 16:9.”

**Optional technical overlay:** `Intent → AgentEnvelope → Specialist call(s) → Guardian output check`

### Agent Scene 2 — Security & Responsible-AI Guardian (about 0:45)

**Purpose:** Explain the Guardian’s input and output checks without presenting it as a complete security guarantee.

**What to show:** Use a safe benign request in the real UI. Then show a separate mock diagram (not a live attack) in which an abstract suspicious instruction is blocked and secret-looking text is redacted. Show the Responsible AI UI for explanations, correcting mood, or flagging recommendations as user-facing controls; identify these as related product controls, not all Guardian internals.

**Narration:** “The Guardian is a safety checkpoint around the agent workflow. On input, it normalizes and sanitizes text, looks for prompt-injection patterns such as requests to reveal hidden instructions or bypass safeguards, and can return a safe refusal notice when a request is flagged. On output, it applies redaction patterns for secret-like values and removes selected unsafe content before the answer is returned. Security events can be recorded for administrator review. This is a rule-based protective layer; it reduces some risks, but it is not a guarantee that every unsafe or private value will be detected. The application also gives users controls to correct a detected mood, see recommendation reasons, and flag results.”

**Technical details to show in small text:** `GuardianAgent.inspect_input()` sanitizes and checks patterns; `inspect_output()` redacts matched secrets and selected unsafe markers; risk events are stored for the security dashboard. Distinguish these implemented checks from a claim of comprehensive moderation.

**GenAI video prompt:** “Create a 10-second abstract security-check animation for a software explainer. A generic text card passes through a shield; a suspicious instruction card is diverted to a neutral blocked symbol; a secret-like string becomes [redacted]; a normal movie request continues. Do not display real prompt text, keys, passwords, user data, or a fake product dashboard. Calm informative tone, no hacker imagery, labels added in editing, 16:9.”

**Optional technical overlay:** `Normalize → Pattern checks → Allow or safe response → Output redaction`

### Agent Scene 3 — Mood & Preference Analysis (about 0:45)

**Purpose:** Show how natural language becomes structured preference signals that other agents can use.

**What to show:** Enter the actual synthetic request `I’m in a relaxed mood, want science fiction, no horror, and have 100 minutes.` Use an overlay to parse it into fields: mood `Relaxed`; preferred genre `Science Fiction`; disliked genre `Horror`; time `100 min`. If the UI offers a mood confirmation/correction control, show it. Avoid claiming the extraction is always correct.

**Narration:** “Mood and Preference Analysis converts a sentence into a compact set of signals. CineSense looks for mood words, supported genres, negative preferences such as ‘no horror,’ and runtime expressions such as ‘100 minutes’ or ‘two hours.’ It can also extract named entities, quoted titles, and people where available. The implementation uses enhanced rules and can optionally use spaCy named-entity recognition. The result is structured data for retrieval and planning, not a psychological diagnosis. The viewer can correct a detected mood when the interface provides that option.”

**Technical details to show in small text:** `MoodPreferenceAgent.analyze()` returns fields such as `mood`, `genres`, `disliked`, `time_available`, `entities`, `detected_moods`, and `nlp_backend`. Mood scoring checks known word patterns and negation; genre matching handles dislike phrases; time parsing converts hours to minutes. Optional spaCy failure falls back to rules.

**GenAI visual prompt:** “Create a 9-second motion graphic showing a sample sentence transforming into four labeled chips: mood, preferred genre, excluded genre, available minutes. Add a small user-edit pencil icon beside the mood chip. Use example values only as illustrative graphics, not as a real extraction log. No faces or mental-health imagery. Clear educational motion design, 16:9.”

**Optional technical overlay:** `Free text → mood + genres + dislikes + entities + minutes`

### Agent Scene 4 — Retrieval & Recommendation (about 0:50)

**Purpose:** Explain candidate search and ranking, including the difference between retrieval and response generation.

**What to show:** Reuse the real recommendation request and actual candidate cards. Add a diagram overlay of catalogue documents represented by title, overview, genre, runtime, cast, mood, and rating. Animate lexical term matching and semantic similarity contributing to a ranked candidate list. Use actual screen result ordering, not invented score numbers.

**Narration:** “Retrieval and Recommendation searches the available movie catalogue and ranks candidates against the structured request. It combines lexical matching through BM25 with semantic hash-vector similarity, then blends those signals with preference and catalogue factors. Optional Sentence Transformers can provide another semantic representation when installed. The retrieval agent can also apply constraints and produce grounded movie details and recommendation reasons. If an optional language model is configured, the system can use it to phrase a response from supplied catalogue context; otherwise a deterministic local response path remains available. Retrieval finds and orders candidates—the language model does not create catalogue facts.”

**Technical details to show in small text:** Retrieval helpers tokenize text, normalize scores, compute cosine similarity for vectors, and create movie dictionaries. Candidate ranking combines text/relevance signals with mood, genre, runtime, rating, pace, and profile context according to request path. Keep precise weights off screen unless you are showing the matching code/path, because not every endpoint uses the same scoring method.

**GenAI video prompt:** “Create an 11-second educational animation of a movie catalogue search. First highlight words shared with a request to represent lexical search; then show related-theme cards lighting up to represent semantic similarity; finally sort blank movie cards into a ranked list. Include catalogue attributes as simple icons for genre, runtime, rating, and mood. Leave names and numbers blank for the real screen recording. Do not fabricate titles, ratings, or scores. 16:9.”

**Optional technical overlay:** `BM25 text relevance + semantic hash-vector similarity + request constraints`

### Agent Scene 5 — Comparison & Explainability (about 0:50)

**Purpose:** Explain the scoring dimensions, mode-specific weights, trade-offs, and grounded explanation.

**What to show:** Select two or more actual movies in the Compare UI. Show one mode, then switch to another and capture the actual reordered result. Zoom into the score breakdown and explanation. If the UI exposes risk reasons, point out one actual example. Do not call a weighted suitability score an objective movie quality score.

**Narration:** “Comparison and Explainability evaluates the selected candidates across mood fit, genre fit, time fit, catalogue rating, pace, and viewing-history fit. The selected mode changes the weights—for example, Best Quality gives rating more influence, while Shortest Option puts more weight on runtime fit. The agent can adjust the ranking for a new scenario and report rank changes. It also calculates potential trade-offs, such as a movie running over the available time or matching a genre the viewer dislikes. It then gives a concise verdict based on the movie facts provided. The scores are transparent decision support, not a universal measure of quality.”

**Technical details to show in small text:** Mode weight table includes `best_mood`, `best_quality`, `shortest`, `most_exciting`, `safest_group`, and `different`. Criteria are normalized and combined as a weighted score; scenario adjustments can change weights/penalties; risk reasons are emitted separately. LLM explanation, when enabled, is grounded in supplied movie facts, with deterministic fallback text otherwise.

**GenAI visual prompt:** “Create a 10-second clean comparison animation with three blank movie cards and six criteria icons: mood, genre, time, rating, pace, history. A mode switch changes the relative emphasis, then cards reorder. Add a separate amber trade-off marker beside one card. No fabricated percentages or movie facts; leave values blank for real screen capture. Professional, readable, 16:9.”

**Optional technical overlay:** `Overall suitability = weighted criteria − scenario penalties`

### Agent Scene 6 — Mood & Time Scheduler (about 0:50)

**Purpose:** Explain how the scheduler makes a practical single-movie or double-feature plan and calculates finish times.

**What to show:** In the real planner, set a time window and buffer, then show the actual plan. If the interface supports finish-by, use a safe example such as `finish by 10:30 PM`. Show the start time, movie finish, buffer, and remaining minutes from the real result. Include the empty-result behavior if a short runtime cannot fit, but do not force a misleading example.

**Narration:** “Mood and Time Scheduler turns the candidate list into a practical watch plan. It subtracts the wind-down buffer from the available time to calculate the movie-time budget. It first looks for a strong single title that uses a useful portion of the window. If no single title is a good fit, it evaluates pairs of suitable movies and can choose a double feature that stays within budget. When a finish-by time is provided, it calculates a suggested start and planned finish. It reports unused time, and if no candidate fits, it says so rather than inventing a plan.”

**Technical details to show in small text:** `MoodTimeSchedulerAgent.plan()` clamps buffer to 0–60 minutes; computes `movie_budget = free_minutes − buffer`; filters movies by runtime; evaluates candidate pairs; calculates suggested start and planned finish from `finish_by`; returns plan type, selected movies, used/remaining minutes, and message.

**GenAI visual prompt:** “Create an 11-second timeline animation. Begin with an available evening window, subtract a clearly separated wind-down buffer, then fit either one movie block or two shorter movie blocks into the remaining budget. Show a finish-by marker and suggested start marker. Use blank time values for editing; no fake recommendation output. Simple clocks and film icons, dark navy, teal and amber, 16:9.”

**Optional technical overlay:** `Available minutes − buffer → single or double feature → start/finish estimate`

### Closing transition after the six agent scenes (about 0:15)

**Narration:** “Together, these six agents turn one natural-language request into a relevant, ranked, explained, and time-aware movie experience. The Orchestrator coordinates the work, and each specialist has a focused responsibility.”

**Visual:** Animate all six labeled nodes briefly, then cut to the actual CineSense result screen. Keep the Orchestrator in the center and all five specialist roles visible exactly once.

**GenAI prompt:** “Create a 6-second closing architecture animation with one central Conversational Orchestrator and exactly five specialist nodes: Guardian, Mood & Preference Analysis, Retrieval & Recommendation, Comparison & Explainability, Mood & Time Scheduler. A request flows in and one movie shortlist flows out. Clean, restrained product design, labels added in post, no fake UI, no extra agents, 16:9.”

---

## GenAI prompts for production

### Voice generation

“Read the provided narration as a clear, friendly university project presenter. Use beginner-friendly English, a natural pace around 130 words per minute, and short pauses between scenes. Sound confident and informative, not like an advertisement. Pronounce CineSense, BM25, FastAPI, SQLite, PostgreSQL, TMDB, and Vite carefully. Do not add claims or change technical details.”

### Subtitles

“Create accurate English subtitles from this narration. Keep technical names exactly as spoken: Conversational Orchestrator, Guardian, Mood & Preference Analysis, Retrieval & Recommendation, Comparison & Explainability, Mood & Time Scheduler, BM25, FastAPI, SQLite, PostgreSQL, TMDB. Maximum two lines at a time, sentence case, synchronized to speech. Do not paraphrase.”

### Background music

“Compose a subtle instrumental background track for a 10-minute AI software demonstration. Warm, thoughtful electronic ambience with a gentle pulse, no vocals, no dramatic tension, no distracting melody. Keep the arrangement sparse under narration and create natural transitions between sections.”

### Thumbnail

“Design a professional 16:9 YouTube thumbnail for a university project video titled CineSense AI. Show an abstract movie discovery interface and a central hub with exactly six small agent nodes. Deep navy, teal, warm amber accents, clear negative space for a large title added later. No fake readable interface text, no real movie posters, no unrelated logos.”

## How to produce and edit the video

1. **Prepare the demo:** Start the backend and frontend using the repository instructions. Confirm the home page and the features you intend to demonstrate work. Use demo/synthetic account data. Decide whether the video will use offline mode or a configured live LLM, and describe that mode accurately.
2. **Make a shot list:** Record separate clips for homepage, chat recommendation, catalogue search/details, similar movies, comparison, planner, calendar, family/group choice, responsible-AI controls, plans, admin, and B2B. Skip a feature if it is not enabled in your environment; state that it is optional.
3. **Record the screen:** Use 1080p, browser zoom 100–110%, and a clean browser window. Move the pointer slowly. Wait for actual results to finish loading. Capture each action from before the click through the result. Record a second take if a tooltip or loading state hides the result.
4. **Generate supporting assets:** Use the scene prompts for opening/closing footage, abstract transitions, diagrams, music, voice, and subtitles. Generate each short clip separately. Add all labels in the video editor so names and spelling remain accurate.
5. **Edit for clarity:** Place narration first, then real screen recordings, then subtle diagrams and captions. Keep music quiet beneath speech. Use slow zooms/callouts to point at interface details. Leave architecture labels on screen long enough to read and avoid fast cuts in technical sections.
6. **Show the workflow:** Ensure at least one continuous demonstration shows the user entering a request, the assistant returning actual candidates, and the explanation. Add brief on-screen agent-flow labels during the result so evaluators can connect the UI to the architecture.
7. **Final check:** Verify all six agents are named correctly, each demonstrated result came from the running system, and optional services are labeled accurately. Review the entire export for accidental personal information, credentials, API keys, or misleading generated UI. Export MP4 H.264 at 1080p with clear AAC audio and captions.

## Rubric coverage checklist

- **Clarity & Explanation (8):** Simple hook, beginner-friendly explanation, clear six-agent diagram, narration follows the user journey.
- **Demonstration (7):** Real end-to-end recommendation plus catalogue, similarity, comparison, planner, and family/group flows.
- **Use of GenAI Tools (5):** Generated opening/closing, diagrams, transitions, voice/captions/music, with prompts documented here.
- **Technical Accuracy (3):** Correct agent count and responsibilities; optional providers and integrations labeled; real results captured from the app.
- **Presentation Quality (2):** 1080p screen capture, legible overlays, captions, clean voice mix, consistent color palette, professional pacing.
