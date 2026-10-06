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


## 🔐 Security and Responsible AI

CineSense includes a Guardian that checks for known prompt-injection patterns and selected sensitive content in generated output. It also supports privacy-conscious security event logging.

Testing found that some obfuscated, encoded, and Sinhala prompts did not receive the expected security response. Security controls are still being evaluated and should not be treated as a guarantee that every attack will be detected.

## 🧪 Testing

The project includes prompt-security tests and an administrative security-assessment feature. Testing should include:

- Malicious prompts to check security handling.
- Benign movie requests to check that normal recommendations still work.
- The actual reply and safety status, rather than only the HTTP status code.

## 🎓 Project Information

CineSense was developed as an academic project for **Information Retrieval and Web Analytics (IT3041)**. It demonstrates the use of information retrieval, natural-language processing, language models, agent communication, and security checks in a movie recommendation application.

## 👥 Contributors

- [Sasheen](https://github.com/sasheen-widanagamage)
- [Theekshana](https://github.com/TheekshanaMayadunna)
- [Sanuja](https://github.com/sanujaandrahennadi)
- [Chamodi](https://github.com/chamodi-kumarage)


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
