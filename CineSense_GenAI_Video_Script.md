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
