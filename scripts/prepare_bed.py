#!/usr/bin/env python3
"""Prepare a music bed for the edit: first beat at 0, exact duration, loudness at -16 LUFS.

Usage:
  python3 prepare_bed.py raw.wav bed.wav --duration 48 [--bpm 120] [--lufs -16]

1. finds the phase of the beat grid (at --bpm) that best matches the low-end onsets and trims the start so that a
   beat falls exactly at 0 (never more than one beat is trimmed);
2. brings the file to the exact duration (trims or pads with silence) with a 5 ms fade at the end;
3. brings the loudness to --lufs (measured with ffmpeg), with the true peak below -1 dBTP (limiter only if needed).
It prints the measured tempo (fine search on the grid): if it is more than 0.05% away from --bpm, over 50 s the
beats drift by more than a frame.
Needs a Python environment with numpy, scipy, soundfile, librosa.
"""
import argparse
import subprocess
import tempfile

import librosa
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt


def grid(env: np.ndarray, sr: int, hop: int, bpm: float) -> tuple:
    """Tempo and phase of the beat grid that best match the onsets: fine search within ±1% of bpm."""
    seconds = len(env) * hop / sr
    best = (-1.0, bpm, 0.0)
    for t in bpm * (1 + np.linspace(-0.01, 0.01, 161)):
        period = 60 / t
        phases = np.arange(0, period, 0.002)
        beats = np.arange(0, seconds - period, period)
        idx = np.clip(np.round((phases[:, None] + beats[None, :]) * sr / hop).astype(int), 0, len(env) - 1)
        scores = env[idx].sum(axis=1)
        k = int(np.argmax(scores))
        if scores[k] > best[0]:
            best = (float(scores[k]), float(t), float(phases[k]))
    return best[1], best[2]


def measure_lufs(path: str) -> tuple:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    i = p = None
    summary = False
    for row in r.stderr.splitlines():
        if "Summary:" in row:
            summary = True
        if summary and row.strip().startswith("I:"):
            i = float(row.split()[1])
        if summary and row.strip().startswith("Peak:"):
            p = float(row.split()[1])
    return i, p


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("source")
    a.add_argument("output")
    a.add_argument("--bpm", type=float, default=120.0)
    a.add_argument("--duration", type=float, required=True, help="seconds")
    a.add_argument("--lufs", type=float, default=-16.0)
    x = a.parse_args()

    y, sr = sf.read(x.source, always_2d=True)
    mono = y.mean(axis=1)
    low = sosfiltfilt(butter(4, 150, "low", fs=sr, output="sos"), mono).astype(np.float32)
    hop = 128
    env = librosa.onset.onset_strength(y=low, sr=sr, hop_length=hop)
    tempo, phase = grid(env, sr, hop, x.bpm)
    drift = 100 * (tempo - x.bpm) / x.bpm
    print(f"first beat phase: {phase * 1000:.1f} ms; measured tempo {tempo:.3f} BPM ({drift:+.3f}%)")
    if abs(drift) > 0.05:
        print("WARNING: over 50 s the beats drift by more than a frame; consider a small speed correction")

    y = y[int(round(phase * sr)):]
    n = int(round(x.duration * sr))
    y = y[:n] if len(y) >= n else np.vstack([y, np.zeros((n - len(y), y.shape[1]))])
    tail = int(0.005 * sr)
    y[-tail:] *= np.linspace(1, 0, tail)[:, None]

    with tempfile.TemporaryDirectory() as tmp:
        raw = f"{tmp}/r.wav"
        sf.write(raw, y, sr, subtype="PCM_24")
        i0, p0 = measure_lufs(raw)
        gain = x.lufs - i0
        filters = f"volume={gain:.2f}dB"
        if p0 + gain > -1.0:
            filters += ",alimiter=limit=0.84:attack=1:release=60:level=false"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", filters, "-c:a", "pcm_s16le", x.output], check=True)
    i1, p1 = measure_lufs(x.output)
    print(f"-> {x.output}: {x.duration:.3f} s, {i1} LUFS, true peak {p1} dBTP (gain {gain:+.1f} dB)")


if __name__ == "__main__":
    main()
