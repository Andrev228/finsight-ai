"""Run live agent routing and grounding evaluations."""

import argparse
import asyncio
import json
from pathlib import Path

import httpx

DEFAULT_DATASET = Path(__file__).parents[1] / "evals" / "cases.json"


async def run(base_url: str, dataset: Path, threshold: float) -> int:
    cases = json.loads(dataset.read_text())
    passed = 0
    unavailable = 0
    async with httpx.AsyncClient(base_url=base_url, timeout=90) as client:
        for case in cases:
            for attempt in range(3):
                response = await client.post(
                    "/api/ai/chat",
                    json={"message": case["question"]},
                )
                if response.status_code < 500 or attempt == 2:
                    break
                await asyncio.sleep(2**attempt)
            if response.status_code >= 400:
                try:
                    detail = response.json().get("detail", {})
                except ValueError:
                    detail = {}
                error_code = (
                    detail.get("error_code", f"HTTP_{response.status_code}")
                    if isinstance(detail, dict)
                    else f"HTTP_{response.status_code}"
                )
                print(f"UNAVAILABLE {case['id']}: {error_code}")
                unavailable += 1
                continue
            body = response.json()
            actual_tools = sorted(body["tools_used"])
            expected_tools = sorted(case["expected_tools"])
            success = (
                actual_tools == expected_tools
                and body["unsupported"] == case["expect_unsupported"]
                and bool(body["answer"].strip())
                and bool(body.get("analytics")) == case["require_analytics"]
                and len(body.get("sources", [])) >= case["min_sources"]
            )
            passed += int(success)
            print(
                f"{'PASS' if success else 'FAIL'} {case['id']}: "
                f"tools={actual_tools}, unsupported={body['unsupported']}",
            )
    evaluated = len(cases) - unavailable
    if not evaluated:
        print("No cases evaluated because the provider was unavailable.")
        return 2
    score = passed / evaluated
    print(
        f"score={score:.3f} ({passed}/{evaluated}), "
        f"unavailable={unavailable}",
    )
    if unavailable:
        return 2
    return 0 if score >= threshold else 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--threshold", type=float, default=1.0)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.base_url, args.dataset, args.threshold)))


if __name__ == "__main__":
    main()
