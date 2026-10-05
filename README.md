<div align="center">

# 🎬 CineSense
### Your mood-aware, multi-agent movie companion

Discover movies that fit your mood, interests, and available time. CineSense combines movie search, personalized recommendations, comparisons, and watch planning in one AI-powered application.

[Features](#-features) · [How It Works](#-how-it-works) · [Technology](#-technology-stack) · [Run Locally](#-run-locally)

</div>

---

## ✨ What is CineSense?

CineSense is an AI-based movie recommendation system that helps users find and plan movies based on what they want to watch. Instead of relying only on a movie title or genre, users can describe their mood, preferences, and available time in natural language.

The system coordinates specialist agents to understand the request, retrieve suitable movies, explain recommendations, and support movie planning. A Guardian Agent provides security and responsible-AI checks around the chat flow.

## 🚀 Features

### 🎭 Mood-aware movie discovery
- Describe your mood or the kind of movie you want in everyday language.
- Receive recommendations based on preferences such as mood, genre, and available time.
- View recommendation reasons, including how a movie matches the request.

### 🔎 Movie search
Search the CineSense catalogue by:

- Movie title
- Actor
- Director
- Mood
- Keyword

### 🎞️ Personalized recommendations
- Discover movies matched to your preferences and time limit.
- Browse top picks and recommendation cards.
- Review movie details such as runtime, year, genres, and rating when available.

### ⚖️ Movie comparison
Compare movies and review their details to help decide what to watch.

### 🗓️ Watch planning
Use the watch-planning features to organize a movie night around your available time and preferences.

### 👨‍👩‍👧 Family plans
CineSense includes a Family Plans area for exploring movie choices for a shared viewing experience.

### 🛡️ Security and responsible-AI features
- Guardian checks incoming chat messages for known prompt-injection patterns.
- The system checks generated output for selected secret-like content and protected prompt markers.
- Security events can be recorded using privacy-conscious details.
- Responsible-AI information is available in the application.

Security testing has identified areas for improvement in handling obfuscated, encoded, and multilingual prompts. The Guardian is a protective layer, not a guarantee that every attack will be detected.

## 🧠 How It Works

```mermaid
flowchart LR
    User["User request"] --> Guardian["Guardian checks input"]
    Guardian --> Orchestrator["Conversational Orchestrator"]
    Orchestrator --> Mood["Mood and preference analysis"]
    Orchestrator --> Retrieval["Movie retrieval and recommendations"]
    Orchestrator --> Compare["Comparison and explanations"]
    Orchestrator --> Planner["Watch planning"]
    Mood --> Orchestrator
    Retrieval --> Orchestrator
    Compare --> Orchestrator
    Planner --> Orchestrator
    Orchestrator --> Output["Guardian checks response"]
    Output --> User
