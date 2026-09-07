# Demo runbook

1. Start Docker services, apply migrations, and run the Next.js frontend.
2. Open the app and connect `First Platypus Bank` through Plaid Sandbox.
3. Sync accounts and transactions through the API docs or the existing Link
   flow.
4. Ask “How much did I spend over the last three months?” to demonstrate
   SQL-only monetary calculation.
5. Ask “Based on my recent spending, how could an emergency fund help me?” to
   demonstrate combined analytics, CFPB retrieval, and citations.
6. Ask for an exact current account balance to demonstrate explicit refusal
   when no supported tool can answer.
7. Show `ai_runs` in PostgreSQL: latency and token metadata are present while
   raw prompts and user IDs are absent.
8. Run the eval command from the README and explain that provider outages are
   separated from quality regressions.

For Stripe, use Stripe CLI to forward test events to
`/api/billing/webhook`; set the emitted signing secret in
`STRIPE_WEBHOOK_SECRET`. Never use live-mode keys in the demo.
