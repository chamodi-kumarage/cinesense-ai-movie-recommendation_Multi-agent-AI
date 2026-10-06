<div align="center">

# 🎬 CineSense

### Your mood-aware, AI-powered movie companion

Find a movie that fits your mood, preferences, and available time.
Explore the catalogue, get recommendations, compare movies, and plan a movie night.

</div>

---

## 📌 About CineSense

CineSense is an AI-powered movie discovery and recommendation system. Users can search for movies or describe what they want in everyday language. The system uses a multi-agent workflow to understand preferences, find suitable movies, explain recommendations, and support movie planning.

## ✨ Features

- **AI movie assistant:** Ask for movie recommendations using natural language.
- **Mood-based discovery:** Find movies based on the mood or viewing experience you want.
- **Time-aware recommendations:** Include the amount of time available when asking for suggestions.
- **Movie catalogue:** Browse movie information stored in the CineSense catalogue.
- **Movie search:** Search by title, actor, director, mood, or keyword.
- **Similar movies:** Discover other movies related to a movie you like.
- **Explainable recommendations:** See reasons why a movie may match your request.
- **Movie comparison:** Compare movies to help decide what to watch.
- **Watch planning:** Plan a movie night around your preferences and available time.
- **Family plans:** Explore movies for family viewing and compare family movie options.
- **Pricing plans page:** View the pricing plans presented by the application.
- **Security checks:** The Guardian checks chat input and selected generated output for known risks.
- **Responsible-AI information:** Review the responsible-AI information provided in the application.

## 🖼️ Application Screenshots

Screenshots are stored in the repository under `docs/images/`. The fixed image width keeps them from taking up the full page; the image height adjusts automatically.

### Home

<p align="center">
  <img src="docs/images/home.png" alt="CineSense home page" width="760">
</p>

### Movie catalogue

<p align="center">
  <img src="docs/images/movie-catalogue.png" alt="CineSense movie catalogue" width="760">
</p>

### AI movie assistant

<p align="center">
  <img src="docs/images/ai-assistant.png" alt="CineSense AI movie assistant" width="760">
</p>

### Mood and available time

<p align="center">
  <img src="docs/images/mood-and-time.png" alt="Mood and available-time options" width="760">
</p>

### Similar movies

<p align="center">
  <img src="docs/images/similar-movies.png" alt="Similar movie recommendations" width="760">
</p>

### Movie comparison

<p align="center">
  <img src="docs/images/movie-comparison.png" alt="Movie comparison screen" width="760">
</p>

### Family plans

<p align="center">
  <img src="docs/images/family-plans.png" alt="CineSense family plans" width="760">
</p>

### Family movie comparison

<p align="center">
  <img src="docs/images/family-comparison.png" alt="Family movie comparison screen" width="760">
</p>

### Pricing plans

<p align="center">
  <img src="docs/images/pricing-plans.png" alt="CineSense pricing plans" width="760">
</p>

## 🧠 How CineSense Works

The user sends a request through the application. The Guardian checks the input, and the Conversational Orchestrator coordinates the specialist agents. The system searches the movie catalogue, prepares recommendations or comparisons, and checks selected output before returning it.

```mermaid
flowchart LR
    User["User request"] --> Guardian["Guardian checks input"]
    Guardian --> Orchestrator["Conversational Orchestrator"]
    Orchestrator --> Mood["Mood and preference analysis"]
    Orchestrator --> Retrieval["Movie search and recommendations"]
    Orchestrator --> Comparison["Comparison and explanations"]
    Orchestrator --> Planning["Watch planning"]
    Mood --> Orchestrator
    Retrieval --> Orchestrator
    Comparison --> Orchestrator
    Planning --> Orchestrator
    Orchestrator --> Output["Guardian checks selected output"]
    Output --> User
