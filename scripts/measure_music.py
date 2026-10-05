#!/usr/bin/env python3
"""Measure a music bed section by section, to choose between several generations without listening to them.

Usage:
  python3 measure_music.py bed.wav --sections "Intro:0-10,Build:10-20,Swell:20-24,Breath:24-30,Groove:30-42,Outro:42-48" [--bpm 120]
  python3 measure_music.py a.wav b.wav c.wav --sections ...      # compare several files

For every section it prints:
- the level (RMS, dBFS);
- the energy below 60 Hz and below 120 Hz (the low end);
- the brightness (energy above 5 kHz and spectral centroid);
- kick hits per beat (low-end onsets on the beat grid);
- when the kick comes in (first beat of the section with a low-end hit);
- the two most frequent bass notes (the strongest note below 200 Hz, every half second).
For the whole file it prints the estimated tempo, the estimated key and the integrated loudness (LUFS, via ffmpeg).
The estimated key comes from the average of the notes (chromagram) and can be wrong: the real key is the note the
bass keeps returning to. Look at the bass column before you tune pitched sound effects.
Needs a Python environment with numpy, scipy, soundfile, librosa (references/tools.md).
"""
import argparse
import subprocess
from collections import Counter

import librosa
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt

NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def db(x: float) -> float:
    return float(20 * np.log10(max(x, 1e-12)))


def band(y: np.ndarray, sr: int, kind: str, fc: float) -> np.ndarray:
    return sosfiltfilt(butter(4, fc, kind, fs=sr, output="sos"), y)


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


def loudness(path: str) -> str:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    i = p = "?"
    summary = False
    for row in r.stderr.splitlines():
        if "Summary:" in row:
            summary = True
        if summary and row.strip().startswith("I:"):
            i = row.split()[1]
        if summary and row.strip().startswith("Peak:"):
            p = row.split()[1]
    return f"{i} LUFS, true peak {p} dBTP"


def key(y: np.ndarray, sr: int) -> str:
    c = librosa.feature.chroma_cqt(y=y.astype(np.float32), sr=sr).mean(axis=1)
    best = max(((np.corrcoef(np.roll(prof, k), c)[0, 1], f"{NOTES[k]} {name}") for prof, name in ((MAJOR, "major"), (MINOR, "minor")) for k in range(12)))
    return f"{best[1]} (correlation {best[0]:.2f})"


def bass_notes(low: np.ndarray, sr: int, a: float, b: float) -> str:
    """The two most frequent bass notes between a and b: the strongest note below 200 Hz, every half second."""
    count = Counter()
    for t in np.arange(a, b - 0.25, 0.5):
        seg = low[int(t * sr):int((t + 0.5) * sr)]
        if len(seg) < sr // 4 or np.sqrt((seg ** 2).mean()) < 1e-3:
            continue
        spectrum = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n=8 * len(seg)))
        f = np.fft.rfftfreq(8 * len(seg), 1 / sr)
        m = (f > 30) & (f < 200)
        n = int(round(12 * np.log2(f[m][np.argmax(spectrum[m])] / 440) + 69))
        count[f"{NOTES[n % 12]}{n // 12 - 1}"] += 1
    return " ".join(k for k, _ in count.most_common(2)) or "-"


def measure(path: str, sections: list, bpm: float) -> None:
    y, sr = sf.read(path, always_2d=True)
    y = y.mean(axis=1)
    lows = band(y, sr, "low", 120)
    sub = band(y, sr, "low", 60)
    highs = band(y, sr, "high", 5000)
    bass = band(y, sr, "low", 200)
    hop = 256
    env = librosa.onset.onset_strength(y=lows.astype(np.float32), sr=sr, hop_length=hop)
    # the grid is measured like in prepare_bed.py (low end below 150 Hz, fine step), so the two scripts agree
    env_g = librosa.onset.onset_strength(y=band(y, sr, "low", 150).astype(np.float32), sr=sr, hop_length=128)
    tempo, phase = grid(env_g, sr, 128, bpm)
    print(f"\n{path}: {len(y) / sr:.3f} s, tempo {tempo:.3f} BPM (first beat at {phase * 1000:.0f} ms), estimated key {key(y, sr)}, {loudness(path)}")
    threshold = np.percentile(env, 90)
    period = 60 / bpm
    print(f"{'section':14s} {'from-to':>9s} {'level':>8s} {'<60 Hz':>8s} {'<120 Hz':>8s} {'>5 kHz':>8s} {'centroid':>11s} {'kick/beat':>10s} {'kick in':>8s}  bass")
    for name, a, b in sections:
        i0, i1 = int(a * sr), int(b * sr)
        seg = y[i0:i1]
        S = np.abs(librosa.stft(seg.astype(np.float32), n_fft=2048, hop_length=512)) ** 2
        freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
        centroid = float((S.sum(axis=1) * freqs).sum() / max(S.sum(), 1e-12))
        beats = np.arange(a, b - 1e-6, period)
        hits = []
        for t in beats:
            k0, k1 = int((t - 0.03) * sr / hop), int((t + 0.03) * sr / hop) + 1
            hits.append(bool(env[max(k0, 0):k1].max(initial=0) >= threshold))
        kick_in = next((f"{t:.2f}" for t, c in zip(beats, hits) if c), "-")
        print(f"{name:14s} {a:4.1f}-{b:4.1f} {db(np.sqrt((seg ** 2).mean())):8.1f} {db(np.sqrt((sub[i0:i1] ** 2).mean())):8.1f} "
              f"{db(np.sqrt((lows[i0:i1] ** 2).mean())):8.1f} {db(np.sqrt((highs[i0:i1] ** 2).mean())):8.1f} {centroid:9.0f} Hz "
              f"{sum(hits) / max(len(hits), 1):10.2f} {kick_in:>8s}  {bass_notes(bass, sr, a, b)}")


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("files", nargs="+")
    a.add_argument("--sections", required=True, help='"Name:from-to,Name:from-to" in seconds')
    a.add_argument("--bpm", type=float, default=120.0)
    x = a.parse_args()
    sections = []
    for piece in x.sections.split(","):
        name, span = piece.split(":")
        start, end = span.split("-")
        sections.append((name.strip(), float(start), float(end)))
    for f in x.files:
        measure(f, sections, x.bpm)


if __name__ == "__main__":
    main()
