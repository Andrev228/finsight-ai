# Deployment

FinSight is a monorepo: a Next.js frontend (`frontend/`) and a FastAPI backend
(`backend/`). The recommended demo topology is **Vercel** for the frontend and a
container host with managed **PostgreSQL (pgvector)** and **Redis** for the
backend. The Azure Bicep in `infra/azure/` remains as an infrastructure-as-code
reference for an all-Azure deployment.

> Security note: the demo uses operator-issued HS256 tokens, not a real identity
> provider. Keep all data synthetic (Plaid Sandbox) and never connect a real
> bank. See `docs/threat-model.md`.

## Frontend — Vercel

1. Push `main` to GitHub (already the source of truth).
2. In Vercel, **Add New Project → Import** the `Andrev228/finsight-ai` repo.
3. Set **Root Directory** to `frontend`. Vercel auto-detects Next.js
   (build `next build`, output handled automatically).
4. Add an environment variable:
   - `NEXT_PUBLIC_API_URL` = the public backend URL (e.g.
     `https://finsight-api.example.com`). This is embedded at build time, so a
     change requires a redeploy.
5. Deploy. Note the resulting origin (e.g. `https://finsight-ai.vercel.app`).

## Backend — container host

The backend image is built from `backend/Dockerfile`. It needs:

- **PostgreSQL** with the `vector` extension (pgvector).
- **Redis** for AI rate limiting.
- Environment/secrets (see `.env.example`): `DATABASE_URL`, `REDIS_URL`,
  `AUTH_JWT_SECRET` (≥32 random bytes), `APP_ENCRYPTION_KEY` (Fernet key),
  `GEMINI_API_KEY`, Plaid Sandbox credentials, Stripe keys, and
  `FRONTEND_ORIGIN` set to the Vercel origin from the step above (required for
  CORS).
- Run migrations on release: `alembic upgrade head`.
- Optionally seed knowledge: `POST /api/ai/knowledge/ingest/{source_id}` with the
  admin key.

Set `APP_ENV=production` and keep `ALLOW_INSECURE_LOCAL_AUTH` /
`ALLOW_INSECURE_LOCAL_ADMIN` disabled.

## Wiring checklist

- [ ] Backend deployed and reachable over HTTPS.
- [ ] `FRONTEND_ORIGIN` on the backend equals the Vercel origin.
- [ ] `NEXT_PUBLIC_API_URL` on Vercel equals the backend origin.
- [ ] `alembic upgrade head` applied against the managed database.
- [ ] Health check green: `GET /api/health`.
