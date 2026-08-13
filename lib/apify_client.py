#!/usr/bin/env python3
"""
Thin, dependency-free wrapper around the Apify REST API.

Design goals:
- No pip installs required (stdlib only: urllib, json, argparse) so a non-technical
  teammate never has to touch a package manager during /ig-setup.
- Every paid call goes through run_actor(), which refuses to run if the estimated
  cost exceeds the caller's budget cap. Apify's pricing changes over time and varies
  by plan tier, so PRICING_PER_1K_USD below is a conservative estimate, not a contract —
  run_actor() always reports the *actual* cost Apify billed (from the run's usage
  stats) so callers can log real spend and keep estimates honest over time.

Field-name gotchas confirmed via live testing on a prior build of this plugin:
- apify/instagram-reel-scraper takes `username` (singular) for BOTH handles and
  direct post/reel URLs — there is no separate `directUrls` field, despite what
  the actor's own docs prose might suggest.
- apify/instagram-followers-count-scraper takes `usernames` (PLURAL) — genuinely
  different from the reel scraper. Easy to mix up; confirmed by hitting a real
  "Field input.username is required" error and correcting it.

CLI usage (what skills shell out to):
    python3 lib/apify_client.py validate-token --token <token>
    python3 lib/apify_client.py estimate-cost --actor <slug> --results <n>
    python3 lib/apify_client.py run-actor --actor <slug> --input '<json>' \\
        --budget-cap <usd> --expected-results <n> [--token <token>]

Exit codes: 0 = success, 1 = budget cap would be exceeded (aborted before spending
anything), 2 = API/network error, 3 = bad input.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API_BASE = "https://api.apify.com/v2"

# Official Apify actors this plugin defaults to. Overridable per-teammate in
# config/user_config.json -> apify.actors, e.g. if Apify deprecates one or a
# teammate prefers a community alternative.
DEFAULT_ACTORS = {
    "reel_scraper": "apify/instagram-reel-scraper",
    "hashtag_scraper": "apify/instagram-hashtag-scraper",
    "follower_count_scraper": "apify/instagram-followers-count-scraper",
}

# Conservative per-1000-results estimates on Apify's free plan. Used only for the
# pre-flight budget check — never for actual billing math (run_actor() always
# reports the real cost Apify billed). Calibrated against real observed costs from
# live testing on a prior build, not just researched documentation, because
# documentation and reality disagreed meaningfully in both directions:
#   - reel-scraper: docs suggested $1.00/1k, observed ~$2.55-2.80/1k
#   - hashtag-scraper: docs suggested $2.60/1k, observed ~$0.48/1k
#   - transcript add-on: docs suggested ~$3.50/1k, observed ~$50/1k at small batch
#     sizes (a 5-reel pull cost $0.2514) — looks closer to a flat ~$0.05/reel than
#     a volume-scaled rate, and every real caller of this add-on (voice-profile,
#     radar's shortlist-only transcription) operates at small batch sizes, so don't
#     assume a per-1000 discount kicks in.
PRICING_PER_1K_USD = {
    "apify/instagram-reel-scraper": 2.80,
    "apify/instagram-reel-scraper:with_transcript": 50.00,
    "apify/instagram-hashtag-scraper": 0.65,
    "apify/instagram-followers-count-scraper": 2.80,
}


class BudgetExceededError(Exception):
    pass


class ApifyAPIError(Exception):
    pass


def _request(method: str, path: str, token: str, body: dict | None = None, timeout: int = 180) -> dict:
    url = f"{API_BASE}{path}"
    if "?" in url:
        url += f"&token={token}"
    else:
        url += f"?token={token}"

    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise ApifyAPIError(f"HTTP {e.code} calling {path}: {detail}") from e
    except urllib.error.URLError as e:
        raise ApifyAPIError(f"Network error calling {path}: {e.reason}") from e


def validate_token(token: str) -> dict:
    """
    Confirms the token works. This hits GET /users/me, which Apify does not bill
    for — there is no meaningful cost to checking a token, despite what older docs
    may imply. Returns {"ok": True, "username": ...} or {"ok": False, "error": ...}.
    """
    try:
        result = _request("GET", "/users/me", token)
        data = result.get("data", {})
        return {"ok": True, "username": data.get("username"), "plan": data.get("plan", {}).get("id")}
    except ApifyAPIError as e:
        return {"ok": False, "error": str(e)}


def estimate_cost(actor: str, expected_results: int, with_transcript: bool = False) -> float:
    key = f"{actor}:with_transcript" if with_transcript and f"{actor}:with_transcript" in PRICING_PER_1K_USD else actor
    per_1k = PRICING_PER_1K_USD.get(key)
    if per_1k is None:
        # Unknown actor (teammate swapped in a custom one) — assume the priciest
        # known rate so we err toward caution rather than silently under-budgeting.
        per_1k = max(PRICING_PER_1K_USD.values())
    return round((expected_results / 1000.0) * per_1k, 4)


def run_actor(
    actor: str,
    run_input: dict,
    token: str,
    budget_cap_usd: float,
    expected_results: int,
    with_transcript: bool = False,
    wait_secs: int = 180,
) -> dict:
    """
    Runs an actor synchronously and returns its dataset items, but only after
    confirming the pre-flight cost estimate fits inside budget_cap_usd. Raises
    BudgetExceededError *before* calling Apify if the estimate is over cap —
    nothing gets spent on a call we refuse to make.

    Returns: {"items": [...], "estimated_cost_usd": float, "actual_cost_usd": float | None,
              "run_id": str}
    """
    est = estimate_cost(actor, expected_results, with_transcript=with_transcript)
    if est > budget_cap_usd:
        raise BudgetExceededError(
            f"Estimated cost ${est:.4f} for {expected_results} results from '{actor}' "
            f"exceeds budget cap ${budget_cap_usd:.4f}. Nothing was run. "
            f"Lower expected_results, raise the cap in config, or split the call."
        )

    encoded_actor = actor.replace("/", "~")
    path = f"/acts/{encoded_actor}/run-sync-get-dataset-items?timeout={wait_secs}"
    items = _request("POST", path, token, body=run_input, timeout=wait_secs + 30)
    if not isinstance(items, list):
        # run-sync-get-dataset-items normally returns a bare JSON array; if Apify
        # wraps an error as an object instead, surface it rather than pretending
        # we got a valid (empty) dataset.
        raise ApifyAPIError(f"Unexpected response shape from {actor}: {items}")

    actual_cost = None
    try:
        runs = _request("GET", f"/acts/{encoded_actor}/runs?desc=true&limit=1", token)
        latest = runs.get("data", {}).get("items", [])
        if latest:
            usage = latest[0].get("usageTotalUsd")
            if usage is not None:
                actual_cost = usage
    except ApifyAPIError:
        pass  # Non-fatal: cost tracking is best-effort, the scrape itself already succeeded.

    return {
        "items": items,
        "estimated_cost_usd": est,
        "actual_cost_usd": actual_cost,
        "actor": actor,
    }


def _load_dotenv() -> None:
    """
    Claude Code's Bash tool doesn't persist shell state (or env vars) between
    calls, so a plain `.env` file with APIFY_API_TOKEN=... never actually reaches
    a later `python3 lib/apify_client.py ...` invocation unless something loads
    it explicitly. This is that something — stdlib only, no python-dotenv needed.
    """
    if os.environ.get("APIFY_API_TOKEN"):
        return
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(repo_root, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def get_token(cli_token: str | None) -> str:
    _load_dotenv()
    token = cli_token or os.environ.get("APIFY_API_TOKEN")
    if not token:
        print(
            "No Apify token found. Pass --token, or set APIFY_API_TOKEN in your "
            "shell/.env. See docs/how-to-get-apify-token.md.",
            file=sys.stderr,
        )
        sys.exit(3)
    return token


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate-token", help="Check that an Apify token works")
    p_validate.add_argument("--token", required=False)

    p_estimate = sub.add_parser("estimate-cost", help="Estimate cost for an actor run without spending anything")
    p_estimate.add_argument("--actor", required=True)
    p_estimate.add_argument("--results", type=int, required=True)
    p_estimate.add_argument("--with-transcript", action="store_true")

    p_run = sub.add_parser("run-actor", help="Run an actor with a hard budget cap")
    p_run.add_argument("--actor", required=True)
    p_run.add_argument("--input", required=True, help="JSON string of actor run input")
    p_run.add_argument("--budget-cap", type=float, required=True)
    p_run.add_argument("--expected-results", type=int, required=True)
    p_run.add_argument("--with-transcript", action="store_true")
    p_run.add_argument("--token", required=False)
    p_run.add_argument("--wait-secs", type=int, default=180)

    args = parser.parse_args()

    if args.command == "validate-token":
        token = get_token(args.token)
        print(json.dumps(validate_token(token)))
        return 0

    if args.command == "estimate-cost":
        cost = estimate_cost(args.actor, args.results, with_transcript=args.with_transcript)
        print(json.dumps({"actor": args.actor, "expected_results": args.results, "estimated_cost_usd": cost}))
        return 0

    if args.command == "run-actor":
        token = get_token(args.token)
        try:
            run_input = json.loads(args.input)
        except json.JSONDecodeError as e:
            print(json.dumps({"ok": False, "error": f"--input is not valid JSON: {e}"}))
            return 3
        try:
            result = run_actor(
                actor=args.actor,
                run_input=run_input,
                token=token,
                budget_cap_usd=args.budget_cap,
                expected_results=args.expected_results,
                with_transcript=args.with_transcript,
                wait_secs=args.wait_secs,
            )
            print(json.dumps({"ok": True, **result}))
            return 0
        except BudgetExceededError as e:
            print(json.dumps({"ok": False, "error": str(e), "reason": "budget_exceeded"}))
            return 1
        except ApifyAPIError as e:
            print(json.dumps({"ok": False, "error": str(e), "reason": "api_error"}))
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
