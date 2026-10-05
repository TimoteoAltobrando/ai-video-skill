#!/usr/bin/env python3
"""Clean plate: the empty room, made from the footage itself (the camera must be on a tripod).

Usage:
  python3 clean_plate.py --video footage.mp4 --mask mask.mkv --out plate.png [--samples 40] [--dilate 25] [--coverage coverage.png]

For every pixel it takes the median of the sampled frames in which the person is NOT there (mask dilated by
--dilate px, so the soft edge and the shadow of the person are excluded too). Pixels the person covers in (almost)
every sample, usually the torso, are filled smoothly from their surroundings ("push-pull": averaged at coarser and
coarser scales, then brought back), never with black: a blur later would drag the black into the edge of the person.
Pixels seen free only a few times are blended with that fill, so the edge of the hole has no dark ring.
--coverage writes how often each pixel was free (white = always).

--mask is a grey mask video with the same frames as --video (person_mask.swift + ffmpeg), or a video with an alpha
channel (VP9 WebM with alpha: the alpha is used). Same size and frame count as the video.
If the camera drifted during the take (more than ~1 px), align the frames first: the plate will be soft otherwise.
Needs numpy, opencv-python, pillow and ffmpeg/ffprobe.
"""
import argparse
import json
import subprocess

import cv2
import numpy as np
from PIL import Image


def probe(path: str) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                        "stream=width,height,nb_read_packets,pix_fmt:stream_tags", "-of", "json", path],
                       capture_output=True, text=True, check=True)
    s = json.loads(r.stdout)["streams"][0]
    tags = {k.lower(): v for k, v in (s.get("tags") or {}).items()}
    return {"w": s["width"], "h": s["height"], "n": int(s["nb_read_packets"]), "alpha": tags.get("alpha_mode") == "1" or "a" in s.get("pix_fmt", "")[:4]}


def sampled(path: str, every: int, w: int, h: int, gray: bool, alpha: bool):
    pre = ["-c:v", "libvpx-vp9"] if alpha else []
    vf = f"select='not(mod(n\\,{every}))'" + (",alphaextract" if alpha else "")
    pix, ch = ("gray", 1) if gray else ("rgb24", 3)
    p = subprocess.Popen(["ffmpeg", "-v", "error", *pre, "-i", path, "-vf", vf, "-fps_mode", "passthrough",
                          "-f", "rawvideo", "-pix_fmt", pix, "-"], stdout=subprocess.PIPE)
    size = w * h * ch
    while True:
        b = p.stdout.read(size)
        if len(b) < size:
            break
        yield np.frombuffer(b, np.uint8).reshape(h, w, ch)
    p.wait()


def push_pull(img: np.ndarray, weight: np.ndarray) -> np.ndarray:
    """Smooth fill of the low-weight pixels: weighted averages at coarser and coarser scales, then back up."""
    levels = []
    num, den = img * weight[..., None], weight.copy()
    while max(den.shape) > 1:
        levels.append((num, den))
        size = (max(1, den.shape[1] // 2), max(1, den.shape[0] // 2))
        num = cv2.resize(num, size, interpolation=cv2.INTER_AREA).reshape(size[1], size[0], -1)
        den = cv2.resize(den, size, interpolation=cv2.INTER_AREA).reshape(size[1], size[0])
    # the top of the pyramid is a single pixel: the weighted average of everything that is known
    mean = (img * weight[..., None]).sum((0, 1)) / max(float(weight.sum()), 1e-6)
    out = np.where(den[..., None] > 1e-6, num / np.maximum(den, 1e-6)[..., None], mean)
    for num, den in reversed(levels):
        up = cv2.resize(out, (den.shape[1], den.shape[0]), interpolation=cv2.INTER_LINEAR)
        known = num / np.maximum(den, 1e-6)[..., None]
        k = np.clip(den * 4, 0, 1)[..., None]
        out = known * k + up * (1 - k)
    return out


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--video", required=True)
    a.add_argument("--mask", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--samples", type=int, default=40)
    a.add_argument("--dilate", type=int, default=25, help="px around the person that also count as covered")
    a.add_argument("--coverage")
    a.add_argument("--min-free", type=float, default=0.1, help="fraction of free samples below which a pixel is filled")
    x = a.parse_args()

    v, m = probe(x.video), probe(x.mask)
    w, h = v["w"], v["h"]
    if (m["w"], m["h"]) != (w, h):
        raise SystemExit(f"mask size {m['w']}x{m['h']} differs from video {w}x{h}")
    every = max(1, v["n"] // x.samples)
    frames = list(sampled(x.video, every, w, h, False, False))
    masks = list(sampled(x.mask, every, w, h, True, m["alpha"]))
    k = min(len(frames), len(masks))
    print(f"{k} samples, one every {every} frames")
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * x.dilate + 1, 2 * x.dilate + 1))
    free = np.stack([cv2.dilate((mm[..., 0] > 5).astype(np.uint8), kernel) == 0 for mm in masks[:k]])
    stack = np.stack(frames[:k])
    plate = np.zeros((h, w, 3), np.uint8)
    step = 64
    for y0 in range(0, h, step):
        s = stack[:, y0:y0 + step].astype(np.float32)
        f = free[:, y0:y0 + step, :, None]
        s[~np.broadcast_to(f, s.shape)] = np.nan
        with np.errstate(all="ignore"), __import__("warnings").catch_warnings():
            __import__("warnings").simplefilter("ignore", RuntimeWarning)
            med = np.nanmedian(s, axis=0)
        plate[y0:y0 + step] = np.nan_to_num(med, nan=0).clip(0, 255).astype(np.uint8)
    coverage = free.mean(axis=0)
    # confidence of the median: 0 below --min-free, 1 from three times that; the rest comes from the smooth fill
    trust = np.clip((coverage - x.min_free) / (2 * x.min_free), 0, 1).astype(np.float32)
    if (trust < 1).any():
        fill = push_pull(plate.astype(np.float32), trust)
        t = cv2.GaussianBlur(trust, (0, 0), 2)[..., None]
        plate = (plate * t + fill * (1 - t)).clip(0, 255).astype(np.uint8)
    Image.fromarray(plate).save(x.out)
    print(f"-> {x.out}; filled: {100 * (trust == 0).mean():.1f}% of the pixels (person almost always there)")
    if x.coverage:
        Image.fromarray((coverage * 255).astype(np.uint8)).save(x.coverage)
        print(f"-> {x.coverage}")


if __name__ == "__main__":
    main()
