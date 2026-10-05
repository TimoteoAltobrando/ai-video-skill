#!/usr/bin/env python3
"""Put a flat object (a framed print, a logo, a sign) on a real wall with the wall's real perspective.

An image model draws added objects straight on the screen, but phone footage is almost never square to the wall:
the phone is a little rotated and the wall a little oblique, so door frames lean and horizontal lines converge.
People notice at once ("the painting doesn't follow physics"). This script measures the two vanishing points of the
wall from straight lines in the plate, derives the camera (focal length and rotation) and warps the object onto the
wall plane, with a soft contact shadow.

1) list the straight lines and pick the ones you trust:
   python3 wall_perspective.py segments plate.png --out lines.png --json lines.json [--min-length 60]
   (lines.png numbers every near-horizontal line in red and every near-vertical one in blue)
2) place the object:
   python3 wall_perspective.py place plate.png --art print.png --rect 318,63,699,443 \
       --lines lines.json --horizontal 3,7,12 --vertical 1,4 --out placed.png [--remove 300,45,716,465] \
       [--shadow 0.3] [--check check.png] [--focal 1500]
   or give the lines directly: --horizontal-xy "x1,y1,x2,y2;x1,y1,x2,y2" --vertical-xy "...".

Which lines: HORIZONTAL = horizontal in the real world and parallel to the wall (door lintel, shelf edges, the line
where the desk meets the wall, a glass door in a parallel wall); not the edge of a curved desk, not a chair leg.
VERTICAL = vertical in the real world (door frames, wall corners, window frames), as long as possible, on both sides.
--rect is where the object would sit if it were straight (x0,y0,x1,y1): its centre and height are kept, its aspect
ratio comes from --art. --remove first erases an existing straight object (and its shadow) with a smooth fill.
Outputs: the plate with the object, a JSON with the 3x3 matrix (art pixels -> image pixels: use it to warp other
layers, e.g. an animated logo, with cv2.warpPerspective or a CSS matrix3d) and, with --check, an image with the
vanishing lines through the object's corners: its edges must follow them.
Needs numpy, opencv-python, pillow.
"""
import argparse
import json
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

G = 2.4


def lin(u8):
    return (u8.astype(np.float32) / 255) ** G


def enc(x):
    return np.clip(x, 0, 1) ** (1 / G)


def detect(gray: np.ndarray, min_length: float) -> list:
    lines = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD).detect(gray)[0]
    out = []
    for x1, y1, x2, y2 in ([] if lines is None else lines.reshape(-1, 4)):
        length = float(np.hypot(x2 - x1, y2 - y1))
        if length < min_length:
            continue
        angle = (np.degrees(np.arctan2(y2 - y1, x2 - x1)) + 180) % 180
        kind = "h" if angle < 15 or angle > 165 else "v" if 75 < angle < 105 else None
        if kind:
            out.append({"id": len(out), "kind": kind, "xy": [round(float(v), 1) for v in (x1, y1, x2, y2)], "length": round(length)})
    return out


def vanishing_point(segs: list, w: int, h: int) -> np.ndarray:
    """least-squares vanishing point (homogeneous, normalised around the centre; long segments weigh more)"""
    rows = []
    for x1, y1, x2, y2 in segs:
        p = np.array([(x1 - w / 2) / 1000, (y1 - h / 2) / 1000, 1.0])
        q = np.array([(x2 - w / 2) / 1000, (y2 - h / 2) / 1000, 1.0])
        l = np.cross(p, q)
        rows.append(l / np.hypot(l[0], l[1]) * np.hypot(x2 - x1, y2 - y1) ** 0.5)
    v = np.linalg.svd(np.array(rows))[2][-1]
    return np.array([v[0] / v[2] * 1000 + w / 2, v[1] / v[2] * 1000 + h / 2, 1.0])


def homography(vh, vv, w, h, rect, art_w, art_h, focal=None):
    c = np.array([w / 2, h / 2])
    f2 = -float((vh[:2] - c) @ (vv[:2] - c))        # two orthogonal directions give the focal length
    f = focal or (float(np.sqrt(f2)) if (0.5 * w) ** 2 < f2 < (1.6 * w) ** 2 else 0.9 * w)
    K = np.array([[f, 0, c[0]], [0, f, c[1]], [0, 0, 1]])
    Ki = np.linalg.inv(K)
    r1 = Ki @ vh
    r1 = r1 / np.linalg.norm(r1) * np.sign(r1[0])  # along the wall, to the right
    r2 = Ki @ vv
    r2 = r2 / np.linalg.norm(r2) * np.sign(r2[1])  # vertical, downwards
    r2 = r2 - (r1 @ r2) * r1
    r2 /= np.linalg.norm(r2)
    x0, y0, x1, y1 = rect
    O = Ki @ np.array([(x0 + x1) / 2, (y0 + y1) / 2, 1.0])   # centre of the object, at depth 1
    side_h = (y1 - y0) / f
    side_w = side_h * art_w / art_h
    A = np.array([[side_w / art_w, 0, -side_w / 2], [0, side_h / art_h, -side_h / 2], [0, 0, 1]])
    M = K @ np.column_stack([r1, r2, O]) @ A
    return M / M[2, 2], f


def push_pull(img: np.ndarray, weight: np.ndarray) -> np.ndarray:
    levels = []
    num, den = img * weight[..., None], weight.copy()
    while max(den.shape) > 1:
        levels.append((num, den))
        size = (max(1, den.shape[1] // 2), max(1, den.shape[0] // 2))
        num = cv2.resize(num, size, interpolation=cv2.INTER_AREA).reshape(size[1], size[0], -1)
        den = cv2.resize(den, size, interpolation=cv2.INTER_AREA).reshape(size[1], size[0])
    mean = (img * weight[..., None]).sum((0, 1)) / max(float(weight.sum()), 1e-6)
    out = np.where(den[..., None] > 1e-6, num / np.maximum(den, 1e-6)[..., None], mean)
    for num, den in reversed(levels):
        up = cv2.resize(out, (den.shape[1], den.shape[0]), interpolation=cv2.INTER_LINEAR).reshape(den.shape[0], den.shape[1], -1)
        known = num / np.maximum(den, 1e-6)[..., None]
        k = np.clip(den * 4, 0, 1)[..., None]
        out = known * k + up * (1 - k)
    return out


def parse_xy(s: str) -> list:
    return [tuple(float(v) for v in p.split(",")) for p in s.split(";") if p.strip()]


def cmd_segments(x) -> None:
    im = Image.open(x.plate).convert("RGB")
    segs = detect(cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2GRAY), x.min_length)
    d = ImageDraw.Draw(im)
    for s in segs:
        x1, y1, x2, y2 = s["xy"]
        col = (255, 40, 0) if s["kind"] == "h" else (0, 110, 255)
        d.line([(x1, y1), (x2, y2)], fill=col, width=3)
        d.text(((x1 + x2) / 2 + 4, (y1 + y2) / 2 + 2), str(s["id"]), fill=col)
    im.save(x.out)
    with open(x.json, "w") as fp:
        json.dump(segs, fp, indent=1)
    print(f"{len(segs)} lines ({sum(s['kind'] == 'h' for s in segs)} near-horizontal, {sum(s['kind'] == 'v' for s in segs)} near-vertical) -> {x.out}, {x.json}")


def cmd_place(x) -> None:
    plate = np.asarray(Image.open(x.plate).convert("RGB"))
    h, w = plate.shape[:2]
    pick = {}
    if x.lines:
        by_id = {s["id"]: s["xy"] for s in json.load(open(x.lines))}
        for key, ids in (("h", x.horizontal), ("v", x.vertical)):
            pick[key] = [tuple(by_id[int(i)]) for i in (ids or "").split(",") if i.strip()]
    if x.horizontal_xy:
        pick["h"] = pick.get("h", []) + parse_xy(x.horizontal_xy)
    if x.vertical_xy:
        pick["v"] = pick.get("v", []) + parse_xy(x.vertical_xy)
    if len(pick.get("h", [])) < 2 or len(pick.get("v", [])) < 2:
        sys.exit("need at least two horizontal and two vertical lines")
    vh, vv = vanishing_point(pick["h"], w, h), vanishing_point(pick["v"], w, h)
    art = Image.open(x.art).convert("RGBA")
    art_a = np.asarray(art).astype(np.float32) / 255
    rect = [float(v) for v in x.rect.split(",")]
    M, f = homography(vh, vv, w, h, rect, art.width, art.height, x.focal)
    room = lin(plate)
    if x.remove:
        rx0, ry0, rx1, ry1 = [int(float(v)) for v in x.remove.split(",")]
        hole = np.ones((h, w), np.float32)
        hole[ry0:ry1, rx0:rx1] = 0
        soft = cv2.GaussianBlur(1 - hole, (0, 0), 3)[..., None]
        room = room * (1 - soft) + push_pull(room, hole) * soft
    rgb = cv2.warpPerspective(lin((art_a[..., :3] * 255).astype(np.uint8)) * art_a[..., 3:], M, (w, h), flags=cv2.INTER_CUBIC)
    alpha = np.clip(cv2.warpPerspective(art_a[..., 3], M, (w, h), flags=cv2.INTER_LINEAR), 0, 1)[..., None]
    scale = (rect[3] - rect[1]) / 380
    shadow = cv2.GaussianBlur(np.roll(np.roll(alpha[..., 0], round(6 * scale), 0), -round(4 * scale), 1), (0, 0), 6 * scale)[..., None]
    room = room * (1 - x.shadow * shadow)
    out = np.clip(rgb, 0, None) + room * (1 - alpha)
    Image.fromarray((enc(out) * 255 + 0.5).astype(np.uint8)).save(x.out)
    corners = cv2.perspectiveTransform(np.array([[[0, 0], [art.width, 0], [art.width, art.height], [0, art.height]]], np.float32), M)[0]
    info = {"matrix_art_to_image": M.tolist(), "vanishing_horizontal": vh[:2].round(1).tolist(), "vanishing_vertical": vv[:2].round(1).tolist(),
            "focal_px": round(f), "corners": corners.round(1).tolist()}
    with open(x.out.rsplit(".", 1)[0] + ".json", "w") as fp:
        json.dump(info, fp, indent=1)
    print(f"-> {x.out}: focal {round(f)} px, vanishing points {vh[:2].round(0).tolist()} and {vv[:2].round(0).tolist()}")
    print(f"   corners {corners.round(1).tolist()}")
    if x.check:
        im = Image.open(x.out).convert("RGB")
        d = ImageDraw.Draw(im)
        for seg, col in [(s, (255, 60, 0)) for s in pick["h"]] + [(s, (0, 120, 255)) for s in pick["v"]]:
            d.line([seg[:2], seg[2:]], fill=col, width=4)          # the lines you picked
        for p in corners:                                          # the vanishing lines through the object's corners
            for v, col in ((vh, (255, 60, 0)), (vv, (0, 120, 255))):
                p = np.array(p, float)
                q = p + (v[:2] - p) * 0.35
                d.line([tuple(p - (q - p)), tuple(q)], fill=col, width=1)
        im.save(x.check)
        print(f"-> {x.check}")


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = a.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("segments")
    s.add_argument("plate")
    s.add_argument("--out", required=True)
    s.add_argument("--json", required=True)
    s.add_argument("--min-length", type=float, default=60)
    p = sub.add_parser("place")
    p.add_argument("plate")
    p.add_argument("--art", required=True)
    p.add_argument("--rect", required=True)
    p.add_argument("--lines")
    p.add_argument("--horizontal")
    p.add_argument("--vertical")
    p.add_argument("--horizontal-xy")
    p.add_argument("--vertical-xy")
    p.add_argument("--remove")
    p.add_argument("--shadow", type=float, default=0.3)
    p.add_argument("--focal", type=float)
    p.add_argument("--out", required=True)
    p.add_argument("--check")
    x = a.parse_args()
    cmd_segments(x) if x.cmd == "segments" else cmd_place(x)


if __name__ == "__main__":
    main()
