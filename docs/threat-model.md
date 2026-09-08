# Threat model

## Protected assets

Plaid access tokens, bank transaction data, conversation history, user
identity, billing state, Gemini and Stripe credentials, administrative
ingestion access, and the integrity of financial answers are protected assets.

## Trust boundaries and mitigations

| Threat | Mitigation | Residual risk |
|---|---|---|
| Cross-tenant data access | Verified JWT `sub`; tenant ID never accepted in request bodies; SQL joins through owner | The included operator-issued HS256 demo token flow must be replaced by OIDC for public use |
| Stolen Plaid token | Fernet encryption at rest; secret is external configuration | Host compromise exposes runtime key |
| Exposed chat-history rows | Fernet-encrypted titles and message content; ownership check before decryption | Runtime key or authenticated application compromise exposes plaintext; raw (pre-redaction) user text is retained encrypted |
| Prompt injection from RAG | Allowlisted admin ingestion; retrieved text labeled untrusted; bounded tools; citation validation | Model may still produce misleading prose |
| LLM data disclosure | Email, phone, government ID, IBAN, and long-number redaction before planner, embedding, and answer calls; prior conversation turns are re-redacted before being replayed to Gemini for multi-turn context | Names and free-form postal addresses need a production DLP service |
| Brute-force/abuse | Redis-backed per-user AI limit; fail closed when Redis is unavailable | Fixed-window bursts are possible at boundary |
| Forged billing events | Stripe HMAC verification, timestamp tolerance, raw-body verification, event ID uniqueness | Webhook secret rotation requires coordinated rollout |
| Admin route exposure | Constant-time key comparison; no implicit local bypass; bypass requires explicit local flags | Local bypass must not be used on a shared network |
| SSRF during ingestion | Fixed source allowlist and server-owned URLs | Allowlisted origin compromise |
| Sensitive telemetry | HMAC fingerprints only; no raw prompt | Low-entropy prompts can still be guessed by an attacker holding the pepper |
| Secret leakage | Secret types, `.env` ignored, Container App secret references | Bicep deployment operators can access supplied secret parameters |

## Data retention

Conversations and chat messages are stored per user with Fernet-encrypted
titles and message bodies. Message content is retained verbatim (the stored
copy is not PII-redacted; redaction is applied only to data leaving the system
toward Gemini). History is kept indefinitely and there is no user-facing
deletion or export endpoint yet; production must add a retention limit and a
delete path to satisfy data-subject requests.

## Operational requirements

Production must set `APP_ENV=production`, disable both insecure bypasses, use
at least 32 random bytes for the JWT secret, rotate all provider credentials,
restrict PostgreSQL networking, and replace the demo Redis container with a
managed highly available service. Logs must not include request bodies,
authorization headers, Plaid tokens, chat messages, or webhook payloads.

This application provides budgeting information, not financial advice. It must
not be used to initiate payments, trade securities, or make credit decisions.
