#!/usr/bin/env python3
"""Music and sound effects with ElevenLabs.

Usage:
  python3 elevenlabs.py credits
  python3 elevenlabs.py music --plan plan.json --seed 1 --out raw/bed-s1.wav
  python3 elevenlabs.py sfx --text "single soft keyboard keystroke, dry, close" --duration 0.5 [--influence 0.5] --out sfx/key.wav

music: model music_v2_5 with a composition plan (JSON with "chunks": text, duration_ms, positive_styles,
       negative_styles, context_adherence). See references/music.md and assets/templates/music-plan.json.
       It never regenerates if the output file already exists: every call costs credits.
sfx:   model eleven_text_to_sound_v2 (/v1/sound-generation).
Output: WAV, 48 kHz, 16 bit (ElevenLabs returns raw PCM; ffmpeg converts it).

API key: the ELEVENLABS_API_KEY environment variable, or the macOS Keychain (service "elevenlabs-api-key").
The key is never printed or written. Next to every audio file there is a .json with the request (without the key)
and the credits it used.
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

BASE = "https://api.elevenlabs.io/v1"


def api_key() -> str:
    k = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not k and sys.platform == "darwin":
        r = subprocess.run(["security", "find-generic-password", "-s", "elevenlabs-api-key", "-w"], capture_output=True, text=True)
        k = r.stdout.strip()
    if not k:
        sys.exit("Missing ElevenLabs key: store it in the Keychain (service elevenlabs-api-key) or in ELEVENLABS_API_KEY")
    return k


def credits() -> dict:
    req = urllib.request.Request(f"{BASE}/user/subscription", headers={"xi-api-key": api_key()})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read())
    return {"used": d.get("character_count"), "limit": d.get("character_limit")}


def post_pcm(path: str, body: dict, dest_pcm: pathlib.Path, timeout: int = 600) -> float:
    url = f"{BASE}{path}?output_format=pcm_48000"
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"xi-api-key": api_key(), "Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} on {path}: {e.read().decode(errors='replace')[:1500]}")
    dest_pcm.parent.mkdir(parents=True, exist_ok=True)
    dest_pcm.write_bytes(data)
    return time.time() - t0


def to_wav(pcm: pathlib.Path, wav: pathlib.Path, expected_seconds: float) -> None:
    """Raw PCM does not say how many channels it has: infer it from the expected duration (16 bit, 48 kHz)."""
    n = pcm.stat().st_size
    channels = 2 if n / (48000 * 2 * expected_seconds) > 1.5 else 1
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", "48000", "-ac", str(channels), "-i", str(pcm),
                    "-c:a", "pcm_s16le", str(wav)], check=True)
    pcm.unlink()
    print(f"-> {wav} ({channels} channels, {n / (48000 * 2 * channels):.3f} s)")


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = a.add_subparsers(dest="what", required=True)
    sub.add_parser("credits")
    m = sub.add_parser("music")
    m.add_argument("--plan", required=True)
    m.add_argument("--seed", type=int, required=True)
    m.add_argument("--out", required=True)
    e = sub.add_parser("sfx")
    e.add_argument("--text", required=True)
    e.add_argument("--duration", type=float, required=True)
    e.add_argument("--influence", type=float, default=0.5, help="prompt_influence, 0-1: how literally to follow the text")
    e.add_argument("--out", required=True)
    x = a.parse_args()

    if x.what == "credits":
        print(credits())
        return
    out = pathlib.Path(x.out)
    if out.exists():
        print(f"{out} already exists: no new generation (delete it to regenerate)")
        return
    before = credits()
    pcm = out.with_suffix(".pcm")
    if x.what == "music":
        plan = json.loads(pathlib.Path(x.plan).read_text())
        seconds = sum(c["duration_ms"] for c in plan["chunks"]) / 1000
        body = {"model_id": "music_v2_5", "seed": x.seed, "composition_plan": plan}
        took = post_pcm("/music", body, pcm)
    else:
        seconds = x.duration
        body = {"text": x.text, "duration_seconds": x.duration, "prompt_influence": x.influence, "model_id": "eleven_text_to_sound_v2"}
        took = post_pcm("/sound-generation", body, pcm, timeout=180)
    to_wav(pcm, out, seconds)
    after = credits()
    used = (after["used"] or 0) - (before["used"] or 0)
    out.with_suffix(".json").write_text(json.dumps({"request": body, "seconds": round(took, 1), "credits": used}, indent=2, ensure_ascii=False))
    print(f"generated in {took:.0f} s, {used} credits (if other jobs share the account, this number includes theirs)")


if __name__ == "__main__":
    main()
