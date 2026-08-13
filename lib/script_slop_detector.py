#!/usr/bin/env python3
"""
Anti-AI-slop gate. Every script /ig-script or /ig-postmortem generates runs through
this before being shown to the teammate. Hard failures block the script and trigger
a regenerate (up to 3 times, per the calling skill); soft warnings are surfaced but
don't block — they're signal for the teammate, not a hard rule.

No third-party NLP libraries — stdlib only (re, statistics), same "no pip install"
philosophy as the rest of lib/.
"""
from __future__ import annotations

import json
import re
import statistics
import sys

# Generic AI-slop phrases that read as ChatGPT-flavored regardless of teammate
# preference — separate from banned_phrases.txt, which is teammate-specific.
AI_SLOP_BASELINE = [
    "delve", "delve into", "in the realm of", "dive into", "dive deep",
    "unlock the power of", "unlock the potential", "elevate", "elevate your",
    "at the end of the day", "it's important to note", "in today's fast-paced world",
    "game-changer", "game changer", "seamlessly", "tapestry",
    "navigate the complexities", "in conclusion", "furthermore", "moreover",
    "whether you're", "let's dive in", "buckle up", "without further ado",
]

MAX_EM_DASHES_PER_100_WORDS = 1.5
SENTENCE_LENGTH_VARIANCE_TOLERANCE = 0.6  # fraction deviation from fingerprint avg before flagging

# Mirrors lib/trends_aggregation.py's TRIGGER_RULES — kept as a light heuristic
# sanity check here, not a hard requirement, since it's approximate by nature.
TRIGGER_HEURISTICS = {
    "controversy_hot_take": re.compile(r"unpopular opinion|hot take|controversial", re.I),
    "fear_fomo": re.compile(r"\bstop doing\b|\bmistake\b|\bwarning\b|before it'?s too late", re.I),
    "transformation_promise": re.compile(r"how i went from|\bbefore\b.{0,20}\bafter\b|\bin \d+\s*(days?|weeks?|months?)\b", re.I),
    "social_proof": re.compile(r"\bmillion\b|\beveryone(?:'s| is)\b|\bviral\b|\d+[kmb]\+?\s*(people|views|watched)", re.I),
    "pain_point": re.compile(r"tired of|struggling with|sick of|why (can'?t|won'?t) (you|i)", re.I),
    "identity_signal": re.compile(r"if you'?re a\b|you know you'?re a\b|every .{0,20} knows", re.I),
    "curiosity_gap": re.compile(r"you won'?t believe|wait (for it|until)|watch (till|until) the end|\?\s*$", re.I),
}


def load_banned_phrases(path: str) -> list[str]:
    phrases = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    phrases.append(line.lower())
    except FileNotFoundError:
        pass
    return phrases


def check_banned_phrases(text: str, banned_phrases: list[str]) -> list[str]:
    text_lower = text.lower()
    return [p for p in banned_phrases if p in text_lower]


def check_ai_slop_baseline(text: str) -> list[str]:
    text_lower = text.lower()
    return [p for p in AI_SLOP_BASELINE if p in text_lower]


def check_em_dash_density(text: str, punctuation_habits: list[str]) -> str | None:
    if "em_dash" in [h.lower().replace("-", "_").replace(" ", "_") for h in (punctuation_habits or [])]:
        return None  # This teammate genuinely uses em-dashes — not a slop signal for them.
    word_count = max(1, len(text.split()))
    em_dash_count = text.count("—") + text.count("--")
    rate_per_100 = (em_dash_count / word_count) * 100
    if rate_per_100 > MAX_EM_DASHES_PER_100_WORDS:
        return f"em-dash rate {rate_per_100:.1f}/100 words exceeds {MAX_EM_DASHES_PER_100_WORDS} and isn't a known habit of this teammate's voice"
    return None


def check_sentence_length_variance(text: str, avg_length_words: float | None) -> str | None:
    if avg_length_words is None:
        return None  # Fingerprint doesn't have this data (e.g. low_confidence, self-description-built) — nothing to compare against.
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    if not sentences:
        return None
    lengths = [len(s.split()) for s in sentences]
    script_avg = statistics.mean(lengths)
    deviation = abs(script_avg - avg_length_words) / max(avg_length_words, 1)
    if deviation > SENTENCE_LENGTH_VARIANCE_TOLERANCE:
        return f"avg sentence length {script_avg:.1f} words deviates {deviation:.0%} from this teammate's fingerprint ({avg_length_words} words)"
    return None


def check_vocabulary_presence(text: str, common_vocabulary: list[str], signature_phrases: list[str]) -> str | None:
    all_terms = (common_vocabulary or []) + (signature_phrases or [])
    if not all_terms:
        return None  # Nothing to check against — a thin/low_confidence fingerprint, not a failure.
    text_lower = text.lower()
    if not any(term.lower() in text_lower for term in all_terms):
        return f"none of this teammate's known vocabulary/signature phrases appear — worth a look, not necessarily wrong"
    return None


def check_trigger_match(text: str, intended_trigger: str | None) -> str | None:
    if not intended_trigger or intended_trigger in ("none", "unclear"):
        return None
    pattern = TRIGGER_HEURISTICS.get(intended_trigger)
    detected = None
    for label, rx in TRIGGER_HEURISTICS.items():
        if rx.search(text):
            detected = label
            break
    if detected and detected != intended_trigger:
        return f"heuristic detected '{detected}' language but script was intended as '{intended_trigger}' — approximate check, worth a human glance, not a hard rule"
    return None


def run_detector(text: str, banned_phrases_path: str | None = None, fingerprint_path: str | None = None,
                  intended_trigger: str | None = None) -> dict:
    hard_failures = []
    soft_warnings = []

    banned_phrases = load_banned_phrases(banned_phrases_path) if banned_phrases_path else []
    banned_hits = check_banned_phrases(text, banned_phrases)
    if banned_hits:
        hard_failures.append(f"banned phrase(s) found: {', '.join(banned_hits)}")

    slop_hits = check_ai_slop_baseline(text)
    if slop_hits:
        hard_failures.append(f"generic AI-slop phrase(s) found: {', '.join(slop_hits)}")

    fingerprint = {}
    if fingerprint_path:
        try:
            with open(fingerprint_path) as f:
                fingerprint = json.load(f)
        except FileNotFoundError:
            pass

    punctuation_habits = fingerprint.get("sentence_structure", {}).get("punctuation_habits", [])
    em_dash_warning = check_em_dash_density(text, punctuation_habits)
    if em_dash_warning:
        hard_failures.append(em_dash_warning)

    avg_length = fingerprint.get("sentence_structure", {}).get("avg_length_words")
    length_warning = check_sentence_length_variance(text, avg_length)
    if length_warning:
        soft_warnings.append(length_warning)

    verbal = fingerprint.get("verbal_patterns", {})
    vocab_warning = check_vocabulary_presence(text, verbal.get("common_vocabulary"), verbal.get("signature_phrases"))
    if vocab_warning:
        soft_warnings.append(vocab_warning)

    trigger_warning = check_trigger_match(text, intended_trigger)
    if trigger_warning:
        soft_warnings.append(trigger_warning)

    return {
        "passed": len(hard_failures) == 0,
        "hard_failures": hard_failures,
        "soft_warnings": soft_warnings,
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text-file", required=True, help="Path to a text file containing the script to check")
    parser.add_argument("--banned-phrases", required=False)
    parser.add_argument("--fingerprint", required=False)
    parser.add_argument("--intended-trigger", required=False)
    args = parser.parse_args()

    with open(args.text_file) as f:
        text = f.read()

    result = run_detector(text, args.banned_phrases, args.fingerprint, args.intended_trigger)
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
