# Six-Agent Architecture

```text
User
  |
  v
Agent 1: Conversational Orchestrator
  |
  +--> Agent 6: Security & Responsible-AI Guardian
  +--> Agent 2: Mood & Preference Analysis
  +--> Agent 3: Retrieval & Recommendation
  +--> Agent 4: Comparison & Explainability
  +--> Agent 5: Mood & Time Scheduler
  |
  +--> Agent 6 output check
  v
User
```

The API layer does not directly compose multiple downstream agents. Agentic flows are routed through the Orchestrator, which is the only caller of the other agent modules.

Each agent hop creates:
```json
{
  "trace_id": "uuid",
  "sender": "orchestrator",
  "receiver": "retrieval",
  "intent": "recommend",
  "payload": {"safe_summary": "..."},
  "timestamp": "ISO-8601"
}
```

Trace payloads hash or summarise private values rather than copying raw chat text.

## Chat sequence
1. User submits text.
2. Orchestrator asks Guardian to inspect it.
3. Orchestrator asks Mood/Preference Agent for structured signals.
4. Orchestrator asks Retrieval Agent for hybrid-ranked candidates.
5. Optional OpenAI-compatible LLM composes the conversational reply from grounded context.
6. Guardian checks the output.
7. Latest 10 encrypted turns are retained for follow-up context.

## Storage
- Users
- Movies
- Encrypted chat turns
- Watch events
- Saved plans
- Recommendation feedback
- Daily AI usage counters
- Agent traces

SQLite is the local default; PostgreSQL is supported through SQLAlchemy `DATABASE_URL`.
