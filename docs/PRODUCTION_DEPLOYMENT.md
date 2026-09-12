# Production deployment

CineSense remains easy to run with SQLite locally, while `docker-compose.prod.yml` is configured for PostgreSQL. Put the backend behind a deployment platform/reverse proxy that terminates HTTPS and forwards requests to port 8000; serve the frontend over the same HTTPS origin or set `FRONTEND_ORIGIN` to its HTTPS URL. In production, authentication cookies automatically use the Secure flag.

Required production secrets: `SECRET_KEY`, `ADMIN_API_KEY`, and `B2B_API_KEY`. Live AI additionally requires an OpenAI or Groq key. Catalogue expansion requires `TMDB_API_KEY`. Real subscription checkout requires the four Stripe settings shown in `.env.example`.

For Stripe, register the webhook endpoint `/api/billing/stripe/webhook` and subscribe at minimum to `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, and `invoice.payment_failed`.

The `/api/health` endpoint is suitable for platform health checks. Privacy-safe HTTP monitoring records are stored in `monitoring_events` and can be read through `/api/monitoring` with `X-Admin-Key`.
