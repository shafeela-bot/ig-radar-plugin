#!/usr/bin/env python3
"""
Phase-2, optional-per-teammate deep video analysis: real cut counts, shot lengths,
and loudness/silence data via ffmpeg, instead of the caption/transcript-based
estimates the rest of this plugin falls back to when ffmpeg isn't installed.

Every caller elsewhere in this plugin checks `which ffmpeg` before touching this
module and skips gracefully if it's missing — this module assumes ffmpeg/ffprobe
ARE present by the time it's called, and doesn't re-check that itself, to avoid
duplicating the same check in two places.

No third-party packages — shells out to the real ffmpeg/ffprobe binaries via
subprocess and parses their stderr text output, which is the standard way to script
against ffmpeg (its analysis output goes to stderr, not stdout, by design).
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys

SCENE_CUT_THRESHOLD = 0.3
SILENCE_NOISE_DB = -30
SILENCE_MIN_DURATION = 0.5
FFMPEG_TIMEOUT_SECS = 60


def is_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def get_duration(video_path: str) -> float | None:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", video_path],
            capture_output=True, text=True, timeout=FFMPEG_TIMEOUT_SECS,
        )
        return float(result.stdout.strip())
    except (subprocess.SubprocessError, ValueError):
        return None


def detect_cuts(video_path: str, threshold: float = SCENE_CUT_THRESHOLD) -> list[float]:
    """
    Real scene-cut timestamps via ffmpeg's scene-change filter, not a guess. Returns
    an empty list (not None) on failure — a video with zero detected cuts and a
    video that failed to analyze look the same to the caller either way, since both
    mean "don't trust cut-count data for this one."
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-i", video_path, "-filter:v", f"select='gt(scene,{threshold})',showinfo",
             "-f", "null", "-"],
            capture_output=True, text=True, timeout=FFMPEG_TIMEOUT_SECS,
        )
        return [float(m) for m in re.findall(r"pts_time:([\d.]+)", result.stderr)]
    except subprocess.SubprocessError:
        return []


def compute_shot_lengths(cut_timestamps: list[float], duration: float) -> dict:
    if not cut_timestamps or not duration:
        return {"avg_cuts_per_second": None, "avg_shot_length_sec": None, "cut_variance": None}

    boundaries = [0.0] + sorted(cut_timestamps) + [duration]
    shot_lengths = [b - a for a, b in zip(boundaries[:-1], boundaries[1:]) if b > a]
    if not shot_lengths:
        return {"avg_cuts_per_second": None, "avg_shot_length_sec": None, "cut_variance": None}

    avg_shot = sum(shot_lengths) / len(shot_lengths)
    variance = sum((s - avg_shot) ** 2 for s in shot_lengths) / len(shot_lengths)
    return {
        "avg_cuts_per_second": round(len(cut_timestamps) / duration, 3),
        "avg_shot_length_sec": round(avg_shot, 2),
        "cut_variance": round(variance, 3),
    }


def detect_silence(video_path: str, noise_db: int = SILENCE_NOISE_DB,
                    min_duration: float = SILENCE_MIN_DURATION) -> list[dict]:
    try:
        result = subprocess.run(
            ["ffmpeg", "-i", video_path, "-af", f"silencedetect=noise={noise_db}dB:d={min_duration}",
             "-f", "null", "-"],
            capture_output=True, text=True, timeout=FFMPEG_TIMEOUT_SECS,
        )
    except subprocess.SubprocessError:
        return []

    starts = [float(m) for m in re.findall(r"silence_start:\s*([\d.]+)", result.stderr)]
    ends = [float(m) for m in re.findall(r"silence_end:\s*([\d.]+)", result.stderr)]
    return [{"start": s, "end": e} for s, e in zip(starts, ends)]


def analyze_loudness(video_path: str) -> dict:
    """
    Uses ffmpeg's ebur128 filter (broadcast-standard loudness measurement) rather
    than the simpler volumedetect filter, since it gives a per-second loudness
    curve, not just a single mean/max — what `voice_fingerprint.json`'s
    `audio_dynamics.loudness_curve_pattern` actually wants.
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-i", video_path, "-af", "ebur128", "-f", "null", "-"],
            capture_output=True, text=True, timeout=FFMPEG_TIMEOUT_SECS,
        )
    except subprocess.SubprocessError:
        return {"loudness_curve_pattern": None, "integrated_loudness_lufs": None}

    per_second = [float(m) for m in re.findall(r"M:\s*(-?[\d.]+)", result.stderr)]
    integrated_match = re.search(r"Integrated loudness:\s*\n\s*I:\s*(-?[\d.]+)", result.stderr)
    integrated = float(integrated_match.group(1)) if integrated_match else None

    pattern = None
    if len(per_second) >= 4:
        first_half = sum(per_second[: len(per_second) // 2]) / (len(per_second) // 2)
        second_half = sum(per_second[len(per_second) // 2 :]) / (len(per_second) - len(per_second) // 2)
        if second_half - first_half > 3:
            pattern = "builds_up"
        elif first_half - second_half > 3:
            pattern = "winds_down"
        else:
            pattern = "steady"

    return {"loudness_curve_pattern": pattern, "integrated_loudness_lufs": integrated}


def full_analysis(video_path: str) -> dict:
    """
    Combines everything into the shape voice_fingerprint.json / outlier breakdowns
    expect: pacing_signature + audio_dynamics. Never raises — a video that fails
    analysis comes back with all-null fields, same as "ffmpeg not run," rather than
    crashing whatever skill called this.
    """
    duration = get_duration(video_path)
    cuts = detect_cuts(video_path) if duration else []
    pacing = compute_shot_lengths(cuts, duration) if duration else {
        "avg_cuts_per_second": None, "avg_shot_length_sec": None, "cut_variance": None,
    }
    silence = detect_silence(video_path)
    loudness = analyze_loudness(video_path)

    silence_total = sum(s["end"] - s["start"] for s in silence)
    silence_usage = None
    if duration:
        silence_usage = "heavy" if silence_total / duration > 0.15 else ("light" if silence_total > 0 else "none")

    return {
        "duration_sec": duration,
        "pacing_signature": pacing,
        "audio_dynamics": {**loudness, "silence_usage": silence_usage},
        "n_cuts_detected": len(cuts),
        "n_silence_intervals": len(silence),
    }


def main() -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video-path", required=True)
    args = parser.parse_args()

    if not is_available():
        print(json.dumps({"ok": False, "error": "ffmpeg/ffprobe not found on this system"}))
        return 1

    print(json.dumps({"ok": True, **full_analysis(args.video_path)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
