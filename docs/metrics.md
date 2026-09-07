# Metrics and ablation

Measurements were taken locally on 2026-09-05 against Plaid Sandbox data and
the Gemini free tier. They are evidence for this build, not production SLOs.

## Quality gates

| Gate | Result |
|---|---:|
| Backend automated tests | 30 passing |
| Eval scenarios | 4 |
| Required live-eval score | 100% |
| Current live-eval status | unavailable: Gemini `RESOURCE_EXHAUSTED` |

Provider failures are excluded from the quality denominator and cause a
separate non-zero exit code. This prevents an outage from being reported as a
model-quality regression while still failing CI.

## Capability ablation

This deterministic ablation reports the maximum fraction of the four eval
intents each tool configuration can support. It is a capability-coverage
measurement, not answer accuracy.

| Configuration | Eval capability coverage |
|---|---:|
| No tools | 25% |
| SQL analytics only | 50% |
| Knowledge RAG only | 50% |
| SQL analytics + knowledge RAG | 100% |

Reproduce with `python backend/scripts/run_ablation.py`.

## Runtime sample

The local telemetry table contained one successful end-to-end Gemini run:
19.63 seconds latency, 548 input tokens, and 52 output tokens. Six recorded
provider/validation failures were retained as error codes without raw prompts.
The sample size is too small for a statistically useful p95 or cost estimate,
so no generalized latency or price claim is made.

For a production benchmark, run at least 100 successful cases per scenario,
report p50/p95/p99 by tool path, pin the model version, and calculate price
from the provider's price sheet at execution time.
