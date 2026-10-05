#!/usr/bin/env python3
"""Animate an image with Seedance via OpenRouter: a first frame and an optional last frame, a clip of a few seconds.

Usage:
  python3 seedance.py --first k1.png [--last k2.png] --prompt "slow dolly-in, ..." --out clip.mp4 \
      [--model bytedance/seedance-2.0-fast] [--resolution 720p] [--duration 5] [--seed 7] \
      [--log docs/spend.md] [--cap 15] [--estimate]

--estimate   only print the expected cost, do not call the service
--log        append a row with the real cost to a markdown table (and read the running total from it)
--cap        in dollars: stop if the logged total plus this estimate would go over it

API key: the OPENROUTER_API_KEY environment variable, or the macOS Keychain (service "openrouter-api-key").
The key is never printed or written.
Indicative prices (September 2026, check openrouter.ai): tokens = width x height x 24 x seconds / 1024;
seedance-2.0 at 1080p 0.0000077 $/token (about 0.37 $/s), at 720p 0.000007; seedance-2.0-fast at 720p 0.0000042
(about 0.09 $/s).
"""
import argparse
import base64
import datetime
import json
import mimetypes
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

API = "https://openrouter.ai/api/v1"
PRICES = {  # dollars per token
    ("bytedance/seedance-2.0", "1080p"): 0.0000077,
    ("bytedance/seedance-2.0", "720p"): 0.000007,
    ("bytedance/seedance-2.0-fast", "720p"): 0.0000042,
}
SIZES = {"1080p": (1920, 1080), "720p": (1280, 720), "480p": (854, 480)}


def api_key() -> str:
    k = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not k and sys.platform == "darwin":
        r = subprocess.run(["security", "find-generic-password", "-s", "openrouter-api-key", "-w"], capture_output=True, text=True)
        k = r.stdout.strip()
    if not k:
        sys.exit("Missing OpenRouter key: store it in the Keychain (service openrouter-api-key) or in OPENROUTER_API_KEY")
    return k


def call(method: str, url: str, data=None, raw=False):
    req = urllib.request.Request(url, method=method, data=json.dumps(data).encode() if data is not None else None,
                                 headers={"Authorization": f"Bearer {api_key()}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            body = r.read()
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} from {url.split('?')[0]}: {e.read().decode(errors='replace')[:800]}")
    return body if raw else json.loads(body)


def data_url(p: str) -> str:
    p = pathlib.Path(p)
    kind = mimetypes.guess_type(p.name)[0] or "image/png"
    return f"data:{kind};base64,{base64.b64encode(p.read_bytes()).decode()}"


def estimate(model: str, resolution: str, seconds: int):
    price = PRICES.get((model, resolution))
    if price is None or resolution not in SIZES:
        return None
    w, h = SIZES[resolution]
    return w * h * 24 * seconds / 1024 * price


def logged_total(log: pathlib.Path) -> float:
    """Sum of the last ("Cost") column of the table rows in the log."""
    if not log.exists():
        return 0.0
    total = 0.0
    for row in log.read_text().splitlines():
        m = re.match(r"^\|\s*\d+\s*\|.*\|\s*([0-9]+[.,][0-9]+)\s*\$\s*\|\s*$", row)
        if m:
            total += float(m.group(1).replace(",", "."))
    return total


def append_log(log: pathlib.Path, clip: str, model: str, resolution: str, seconds: int, cost: float) -> None:
    if not log.exists():
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text("# Seedance spend (OpenRouter)\n\n| # | Date | Clip | Model | Duration | Cost |\n|---|---|---|---|---|---|\n")
    n = sum(1 for r in log.read_text().splitlines() if re.match(r"^\|\s*\d+\s*\|", r)) + 1
    today = datetime.date.today().isoformat()
    with log.open("a") as fp:
        fp.write(f"| {n} | {today} | {clip} | {model.split('/')[-1]} {resolution} | {seconds} s | {cost:.2f} $ |\n")


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--first", required=True, help="first frame (image)")
    a.add_argument("--last", help="optional last frame (image)")
    a.add_argument("--prompt", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--model", default="bytedance/seedance-2.0-fast")
    a.add_argument("--resolution", default="720p")
    a.add_argument("--duration", type=int, default=5)
    a.add_argument("--seed", type=int)
    a.add_argument("--log")
    a.add_argument("--cap", type=float)
    a.add_argument("--estimate", action="store_true")
    x = a.parse_args()

    expected = estimate(x.model, x.resolution, x.duration)
    print(f"estimate: {expected:.2f} $" if expected is not None else "estimate: unknown price for this model and resolution")
    log = pathlib.Path(x.log) if x.log else None
    if log and x.cap is not None:
        spent = logged_total(log)
        print(f"spent so far: {spent:.2f} $ of {x.cap:.2f} $")
        if expected is not None and spent + expected > x.cap:
            sys.exit("stopped: this would go over the spending cap")
    if x.estimate:
        return

    frames = [{"type": "image_url", "image_url": {"url": data_url(x.first)}, "frame_type": "first_frame"}]
    if x.last:
        frames.append({"type": "image_url", "image_url": {"url": data_url(x.last)}, "frame_type": "last_frame"})
    data = {"model": x.model, "prompt": x.prompt, "duration": x.duration, "resolution": x.resolution,
            "aspect_ratio": "16:9", "generate_audio": False, "frame_images": frames,
            "provider": {"options": {"seed": {"parameters": {"watermark": False, "output_format": "mp4"}}}}}
    if x.seed is not None:
        data["seed"] = x.seed
    job = call("POST", f"{API}/videos", data)
    jid = job.get("id") or sys.exit(f"no id in the response: {job}")
    url = job.get("polling_url") or f"{API}/videos/{jid}"
    if url.startswith("/"):
        url = "https://openrouter.ai" + url
    print(f"submitted {jid}", flush=True)
    t0 = time.time()
    while True:
        state = call("GET", url)
        s = state.get("status")
        print(f"{int(time.time() - t0)} s: {s}", flush=True)
        if s == "completed":
            break
        if s in ("failed", "cancelled", "expired"):
            sys.exit(f"failed: {state.get('error') or state}")
        time.sleep(15)
    video = call("GET", f"{API}/videos/{jid}/content?index=0", raw=True)
    out = pathlib.Path(x.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(video)
    usage = state.get("usage") or {}
    cost = usage.get("cost") if isinstance(usage, dict) else None
    cost = float(cost) if cost is not None else (expected or 0.0)
    print(f"saved {out} ({len(video) // 1024} KB), cost {cost:.2f} $")
    if log:
        append_log(log, out.stem, x.model, x.resolution, x.duration, cost)
        print(f"logged in {log}: total {logged_total(log):.2f} $")


if __name__ == "__main__":
    main()
