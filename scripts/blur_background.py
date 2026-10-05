#!/usr/bin/env python3
"""Lens-like blurred background behind a sharp person ("portrait mode" for a whole take).

Usage:
  python3 blur_background.py --video footage.mp4 --mask mask.mkv --plate plate.png --out room.mp4 \
      [--layer person.webm] [--blurred-plate blurred.png] [--radius 13] [--background-ev -0.3] [--person-ev 0] \
      [--wrap 0.10] [--vignette 0.14] [--grain auto] [--processes 4] [--start N --count M]
  python3 blur_background.py --video footage.mp4 --mask mask.mkv --plate plate.png --test 2850 --test-out test.png

Inputs (same size, same frames):
  --video   the take in SDR (hdr_to_sdr.sh), camera on a tripod;
  --mask    the person: grey mask video (person_mask.swift + ffmpeg) or a video with alpha (VP9 WebM);
  --plate   the room without the person in the same framing: clean_plate.py, or a furnished/AI-dressed version of
            it aligned to the real room. The person stays the real pixels of the take; only the room is replaced.
Outputs:
  --out            the person (sharp, untouched colours) on the blurred room, H.264;
  --layer          optional: the person alone with alpha (VP9 WebM, straight alpha) to put graphics BETWEEN the room
                   and the person. Composite it over --blurred-plate (or your own room-only layer), never over --out:
                   --out already contains the person, and a second pass darkens the edges (a dark rim = "cut out");
  --blurred-plate  optional: the blurred empty room as PNG (the background for --layer).

What makes it look real (each one is small, together they remove the cut-out look):
  - disk blur (like an aperture) in linear light, strong highlights boosted first so lamps become soft discs;
  - the mask is averaged over 7 frames, but only where the image did not change (no trails on moving hands);
  - the mask's faint veil below 0.10 is removed with a short ramp: no soft halo;
  - within 2.5 px of the outline the person's colour is taken from inside the figure: no light rim from the old wall;
  - a gentle light wrap (normal blend, 0.10): the "screen" blend usually suggested makes a white rim on bright walls;
  - the phone's grain, measured on the real wall, is added to the blurred room too (one grain everywhere).
Sizes: --radius 13 px at 1080p is a portrait look for a wall ~2.5 m behind a person ~1 m from the camera; a 1.3x
crop in the edit makes it 17 px, like a longer lens. Try --test on 3-4 frames and show them before the full run.
Needs numpy, opencv-python, pillow and ffmpeg (with libvpx-vp9 for alpha in and out).
"""
import argparse
import json
import pathlib
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor

import cv2
import numpy as np
from PIL import Image

G = 2.4          # working gamma (linear light = encoded ** G)
VEIL = 0.10      # alpha below this is removed
EDGE = 2.5       # px from the outline where the colour comes from inside the figure
WRAP_PX = 6.0    # width of the light wrap band
MARGIN = 24      # work only inside the person's bounding box plus this margin


def enc(x):
    return np.clip(x, 0, 1) ** (1 / G)


def probe(path: str) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                        "stream=width,height,r_frame_rate,nb_read_packets,pix_fmt:stream_tags", "-of", "json", path],
                       capture_output=True, text=True, check=True)
    s = json.loads(r.stdout)["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    tags = {k.lower(): v for k, v in (s.get("tags") or {}).items()}
    return {"w": s["width"], "h": s["height"], "fps": float(num) / float(den), "n": int(s["nb_read_packets"]),
            "alpha": tags.get("alpha_mode") == "1" or s.get("pix_fmt", "").startswith("yuva")}


def disk(r: int) -> np.ndarray:
    k = np.zeros((2 * r + 1, 2 * r + 1), np.float32)
    cv2.circle(k, (r, r), r, 1.0, -1, lineType=cv2.LINE_AA)
    return k / k.sum()


def shoulder(x, k=0.85):
    """above k the light is compressed softly towards 1 (boosted highlights do not become flat white blobs)"""
    return np.where(x < k, x, k + (1 - k) * np.tanh((x - k) / (1 - k))).astype(np.float32)


def fill_from(X, w, s):
    """average of X weighted by w in a Gaussian neighbourhood of radius s (colour taken from inside the figure)"""
    den = cv2.GaussianBlur(w, (0, 0), s)
    num = np.stack([cv2.GaussianBlur(X[..., c] * w, (0, 0), s) for c in range(X.shape[-1])], -1)
    return num / np.maximum(den, 1e-6)[..., None], den


def blurred_room(plate_path: str, radius: int, ev: float, vignette: float) -> np.ndarray:
    room = (np.asarray(Image.open(plate_path).convert("RGB")).astype(np.float32) / 255) ** G
    h, w = room.shape[:2]
    Y = enc(room @ np.array([0.2126, 0.7152, 0.0722], np.float32))
    spots = np.clip((Y - 0.93) / 0.06, 0, 1) * np.clip((Y - cv2.GaussianBlur(Y, (0, 0), 25) - 0.03) / 0.07, 0, 1)
    room = room * (1 + 3 * spots[..., None])
    out = cv2.filter2D(room, -1, disk(radius), borderType=cv2.BORDER_REFLECT) * (2 ** ev)
    if vignette:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        out = out * (1 - vignette * (((xx - w / 2) / (0.57 * w)) ** 2 + ((yy - 0.435 * h) / (0.57 * w)) ** 2))[..., None]
    return shoulder(out)


def reader(path: str, start: int, count: int, fps: float, pix: str, alpha=False):
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{max(0.0, (start - 0.5) / fps):.4f}"] + (["-c:v", "libvpx-vp9"] if alpha else [])
    cmd += ["-i", path, "-frames:v", str(count), "-fps_mode", "passthrough"] + (["-vf", "alphaextract"] if alpha else [])
    return subprocess.Popen(cmd + ["-f", "rawvideo", "-pix_fmt", pix, "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=1 << 24)


def unit_grain() -> float:
    r = cv2.GaussianBlur(np.random.default_rng(0).standard_normal((512, 512)).astype(np.float32), (0, 0), 0.7)
    return float((r - cv2.GaussianBlur(r, (0, 0), 2)).std())


def measure_grain(video: str, mask: str, info: dict, minfo: dict) -> np.ndarray:
    """high-frequency noise of the real room (away from the person) on five frames, per channel"""
    w, h, vals = info["w"], info["h"], []
    for n in np.linspace(info["n"] * 0.1, info["n"] * 0.9, 5).astype(int):
        v = reader(video, int(n), 1, info["fps"], "rgb24")
        m = reader(mask, int(n), 1, info["fps"], "gray", minfo["alpha"])
        bv, bm = v.stdout.read(w * h * 3), m.stdout.read(w * h)
        v.wait(); m.wait()
        if len(bv) < w * h * 3 or len(bm) < w * h:
            continue
        I = np.frombuffer(bv, np.uint8).reshape(h, w, 3).astype(np.float32) / 255
        far = cv2.dilate((np.frombuffer(bm, np.uint8).reshape(h, w) > 5).astype(np.uint8), np.ones((61, 61), np.uint8)) == 0
        hp = I - cv2.GaussianBlur(I, (0, 0), 2)
        flat = far & (cv2.GaussianBlur(np.abs(hp).mean(-1), (0, 0), 6) < 0.01)   # flat wall only, not edges
        if flat.sum() > 5000:
            vals.append(hp[flat].std(0))
    return np.median(vals, 0).astype(np.float32) if vals else np.array([0.0025, 0.0027, 0.004], np.float32)


class Grain:
    """four ready grain fields, each cropped at random every frame (generating it every frame is slow)"""

    def __init__(self, seed, sigma, h, w):
        self.r = np.random.default_rng(seed)
        k = unit_grain()
        self.h, self.w = h, w
        self.bank = [cv2.GaussianBlur(self.r.standard_normal((h + 64, w + 64, 3), dtype=np.float32), (0, 0), 0.7) * (sigma / k) for _ in range(4)]

    def __call__(self):
        b = self.bank[int(self.r.integers(4))]
        dy, dx = (int(v) for v in self.r.integers(0, 64, 2))
        return b[dy:dy + self.h, dx:dx + self.w]


def box(a, h, w, m=MARGIN):
    rows, cols = np.flatnonzero(a.any(1)), np.flatnonzero(a.any(0))
    if len(rows) == 0:
        return None
    return max(0, rows[0] - m), min(h, rows[-1] + 1 + m), max(0, cols[0] - m), min(w, cols[-1] + 1 + m)


def composite(I_lin, a, room, room_enc, wrap_src, g, person_ev, wrap):
    """-> (composite, encoded person colour inside the box, final alpha, box)"""
    h, w = a.shape
    a = np.clip((a - VEIL) / (1 - VEIL), 0, 1).astype(np.float32)
    y = room_enc + g
    bx = box(a > 0, h, w)
    if bx is None:
        return np.clip(y, 0, 1), None, a, None
    y0, y1, x0, x1 = bx
    ac, I = a[y0:y1, x0:x1], I_lin[y0:y1, x0:x1]
    d = cv2.distanceTransform((ac >= 0.5).astype(np.uint8), cv2.DIST_L2, 5)
    deep = (d >= EDGE + 1.5).astype(np.float32)
    C1, w1 = fill_from(I, deep, 2.0)
    C2, _ = fill_from(I, deep, 7.0)
    t1 = np.clip(w1 / 0.2, 0, 1)[..., None]
    t = np.clip((d - EDGE) / 1.5, 0, 1)[..., None]
    F = (t * I + (1 - t) * (t1 * C1 + (1 - t1) * C2)) * (2 ** person_ev)
    yF = enc(F)
    band = ((ac >= 0.98) * np.clip(1 - d / WRAP_PX, 0, 1)).astype(np.float32)[..., None]
    yF = yF + wrap * band * (wrap_src[y0:y1, x0:x1] - yF)
    a3 = ac[..., None]
    y[y0:y1, x0:x1] = enc(a3 * yF ** G + (1 - a3) * room[y0:y1, x0:x1]) + (1 - a3) * g[y0:y1, x0:x1]
    return np.clip(y, 0, 1), np.clip(yF, 0, 1), a, bx


def layer_frame(yF, a, bx, h, w, gamma_fix):
    """the person with straight alpha; colour extended 12 px outside the edge (protects it from chroma subsampling)"""
    out = np.zeros((h, w, 4), np.uint16)
    if bx is None:
        return out
    y0, y1, x0, x1 = bx
    ac = a[y0:y1, x0:x1]
    E, _ = fill_from(yF, (ac > 0.5).astype(np.float32), 4.0)
    outside = cv2.distanceTransform((ac <= 0).astype(np.uint8), cv2.DIST_L2, 5)
    c = np.where((ac > 0)[..., None], yF, np.where((outside <= 12)[..., None], E, 0))
    if gamma_fix:   # only for compositors that decode this layer with a different transfer than the room video
        c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4) ** (1 / 2.2)
    out[y0:y1, x0:x1] = (np.dstack([np.clip(c, 0, 1), ac]) * 65535 + 0.5).astype(np.uint16)
    return out


def chunk(job):
    (i, n0, n1, x, info, minfo, sigma, tmp) = job
    cv2.setNumThreads(2)
    h, w, fps, N = info["h"], info["w"], info["fps"], info["n"]
    room = blurred_room(x.plate, x.radius, x.background_ev, x.vignette)
    room_enc, wrap_src = enc(room), enc(cv2.GaussianBlur(room, (0, 0), 8))
    grain = Grain(1000 + i, sigma, h, w)
    c0, c1 = max(0, n0 - 3), min(N, n1 + 3)
    rv = reader(x.video, c0, c1 - c0, fps, "rgb48le")
    rm = reader(x.mask, c0, c1 - c0, fps, "gray", minfo["alpha"])
    tags = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv"]
    wv = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", f"{fps}", "-i", "-",
                           "-vf", "scale=out_color_matrix=bt709:out_range=limited,format=yuv420p", "-c:v", "libx264", "-preset", "fast",
                           "-crf", "14", "-g", f"{round(fps)}", "-threads", "2", *tags, f"{tmp}/room-{i:03d}.mp4"], stdin=subprocess.PIPE)
    wl = None
    if x.layer:
        wl = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba64le", "-s", f"{w}x{h}", "-r", f"{fps}", "-i", "-",
                               "-vf", "scale=out_color_matrix=bt709:out_range=limited,format=yuva420p", "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
                               "-crf", "20", "-b:v", "0", "-auto-alt-ref", "0", "-g", f"{round(fps)}", "-row-mt", "1", "-deadline", "good",
                               "-cpu-used", "5", "-threads", "3", *tags, f"{tmp}/layer-{i:03d}.webm"], stdin=subprocess.PIPE)
    lum = np.array([0.2126, 0.7152, 0.0722], np.float32) / 65535
    buf = {}

    def emit(m):
        u, Iq, a0 = buf[m]
        a = a0
        bx = box(a0 > 0, h, w)
        if bx is not None:
            # mask averaged over the 7 neighbouring frames, only where the image did not change (> 4 levels of 255)
            y0, y1, x0, x1 = bx
            num, den = a0[y0:y1, x0:x1].copy(), np.ones((y1 - y0, x1 - x0), np.float32)
            for k in range(m - 3, m + 4):
                if k == m or k not in buf:
                    continue
                wk = np.clip(1 - (np.abs(buf[k][1][y0:y1, x0:x1] - Iq[y0:y1, x0:x1]) - 3 / 255) / (2 / 255), 0, 1)
                num += wk * buf[k][2][y0:y1, x0:x1]
                den += wk
            a = a0.copy()
            a[y0:y1, x0:x1] = num / den
        I_lin = (u.astype(np.float32) / 65535) ** G
        y, yF, af, bx2 = composite(I_lin, a, room, room_enc, wrap_src, grain(), x.person_ev, x.wrap)
        wv.stdin.write((y * 255 + 0.5).astype(np.uint8).tobytes())
        if wl:
            wl.stdin.write(layer_frame(yF, af, bx2, h, w, x.layer_gamma_fix).tobytes())

    nxt = n0
    for n in range(c0, c1):
        bv, bm = rv.stdout.read(w * h * 6), rm.stdout.read(w * h)
        if len(bv) < w * h * 6 or len(bm) < w * h:
            break
        u = np.frombuffer(bv, np.uint16).reshape(h, w, 3)
        buf[n] = (u, cv2.GaussianBlur(u @ lum, (0, 0), 1.0), np.frombuffer(bm, np.uint8).reshape(h, w).astype(np.float32) / 255)
        while nxt < n1 and (nxt + 3 <= n or n == c1 - 1):
            emit(nxt)
            nxt += 1
            for k in [k for k in buf if k < nxt - 3]:
                del buf[k]
    while nxt < n1 and nxt in buf:      # the stream ended early: flush what is left
        emit(nxt)
        nxt += 1
    for p in [wv] + ([wl] if wl else []):
        p.stdin.close()
        p.wait()
    rv.wait(); rm.wait()
    return i, nxt - n0


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--video", required=True)
    a.add_argument("--mask", required=True)
    a.add_argument("--plate", required=True)
    a.add_argument("--out")
    a.add_argument("--layer")
    a.add_argument("--blurred-plate")
    a.add_argument("--radius", type=int, default=13, help="disk blur radius in px")
    a.add_argument("--background-ev", type=float, default=-0.3, help="room exposure in stops (slightly darker lets the face stand out)")
    a.add_argument("--person-ev", type=float, default=0.0, help="person exposure in stops (whole figure, no masks inside it)")
    a.add_argument("--wrap", type=float, default=0.10)
    a.add_argument("--vignette", type=float, default=0.14)
    a.add_argument("--grain", default="auto", help='"auto" (measured on the real room) or "R,G,B" high-pass std, e.g. 0.0025,0.0027,0.004')
    a.add_argument("--processes", type=int, default=4)
    a.add_argument("--start", type=int, default=0)
    a.add_argument("--count", type=int)
    a.add_argument("--test", type=int, help="render only this frame (no temporal averaging) to --test-out")
    a.add_argument("--test-out", default="test.png")
    a.add_argument("--layer-gamma-fix", action="store_true", help="see layer_frame(): only if your compositor needs it")
    x = a.parse_args()

    info, minfo = probe(x.video), probe(x.mask)
    if (minfo["w"], minfo["h"]) != (info["w"], info["h"]):
        sys.exit(f"mask {minfo['w']}x{minfo['h']} and video {info['w']}x{info['h']} differ")
    sigma = measure_grain(x.video, x.mask, info, minfo) if x.grain == "auto" else np.array([float(v) for v in x.grain.split(",")], np.float32)
    print(f"grain (high-pass std R,G,B): {np.round(sigma, 4).tolist()}")
    h, w = info["h"], info["w"]
    if x.blurred_plate or x.test is not None:
        room = blurred_room(x.plate, x.radius, x.background_ev, x.vignette)
        if x.blurred_plate:
            Image.fromarray((enc(room) * 255 + 0.5).astype(np.uint8)).save(x.blurred_plate)
            print(f"-> {x.blurred_plate}")
    if x.test is not None:
        rv = reader(x.video, x.test, 1, info["fps"], "rgb48le")
        rm = reader(x.mask, x.test, 1, info["fps"], "gray", minfo["alpha"])
        u = np.frombuffer(rv.stdout.read(w * h * 6), np.uint16).reshape(h, w, 3)
        m = np.frombuffer(rm.stdout.read(w * h), np.uint8).reshape(h, w).astype(np.float32) / 255
        y, _, _, _ = composite((u.astype(np.float32) / 65535) ** G, m, room, enc(room), enc(cv2.GaussianBlur(room, (0, 0), 8)),
                               Grain(7, sigma, h, w)(), x.person_ev, x.wrap)
        Image.fromarray((y * 255 + 0.5).astype(np.uint8)).save(x.test_out)
        print(f"-> {x.test_out}")
        return
    if not x.out:
        sys.exit("--out is required (or use --test)")
    n_end = info["n"] if x.count is None else min(info["n"], x.start + x.count)
    total = n_end - x.start
    step = -(-total // x.processes)
    with tempfile.TemporaryDirectory(dir=pathlib.Path(x.out).resolve().parent) as tmp:
        jobs = [(i, x.start + i * step, min(n_end, x.start + (i + 1) * step), x, info, minfo, sigma, tmp)
                for i in range(x.processes) if x.start + i * step < n_end]
        with ProcessPoolExecutor(len(jobs)) as ex:
            for i, done in ex.map(chunk, jobs):
                print(f"chunk {i}: {done} frames", flush=True)
        for name, ext, target in (("room", "mp4", x.out), ("layer", "webm", x.layer)):
            if not target:
                continue
            lst = pathlib.Path(tmp) / f"{name}.txt"
            lst.write_text("".join(f"file '{tmp}/{name}-{j[0]:03d}.{ext}'\n" for j in jobs))
            extra = ["-movflags", "+faststart"] if ext == "mp4" else []
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", *extra, target], check=True)
            print(f"-> {target}")


if __name__ == "__main__":
    main()
