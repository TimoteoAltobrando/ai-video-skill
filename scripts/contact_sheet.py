#!/usr/bin/env python3
"""Contact sheet: several frames in one image, each with its name above it.

Usage:
  python3 contact_sheet.py --video film.mp4 --frames 30,120,288,300 --out sheet.jpg [--fps 24] [--columns 4] [--width 640]
  python3 contact_sheet.py --images out/f*.png --out sheet.jpg [--columns 3]

With --video it extracts the frames with ffmpeg (frame numbers of the film, not seconds).
Needs Pillow (pip install pillow) and, with --video, ffmpeg.
"""
import argparse
import pathlib
import subprocess
import tempfile

from PIL import Image, ImageDraw


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--video")
    a.add_argument("--frames", help="comma-separated frame numbers")
    a.add_argument("--fps", type=float, default=24)
    a.add_argument("--images", nargs="*")
    a.add_argument("--out", required=True)
    a.add_argument("--columns", type=int, default=4)
    a.add_argument("--width", type=int, default=640, help="width of each tile")
    x = a.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        items = []
        if x.video:
            for f in [int(v) for v in x.frames.split(",")]:
                p = pathlib.Path(tmp) / f"f{f:05d}.png"
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{f / x.fps + 0.001:.4f}", "-i", x.video, "-frames:v", "1", str(p)], check=True)
                items.append((f"f{f}", p))
        for p in x.images or []:
            items.append((pathlib.Path(p).stem, pathlib.Path(p)))
        if not items:
            raise SystemExit("nothing to put in the sheet")
        images = [(name, Image.open(p).convert("RGB")) for name, p in items]
        w = x.width
        h = round(w * images[0][1].height / images[0][1].width)
        rows = (len(images) + x.columns - 1) // x.columns
        sheet = Image.new("RGB", (w * x.columns, (h + 22) * rows), (30, 30, 30))
        d = ImageDraw.Draw(sheet)
        for i, (name, im) in enumerate(images):
            cx, cy = (i % x.columns) * w, (i // x.columns) * (h + 22)
            sheet.paste(im.resize((w, h)), (cx, cy + 22))
            d.text((cx + 6, cy + 5), name, fill=(230, 230, 230))
        sheet.save(x.out, quality=85)
        print(f"-> {x.out} ({sheet.width}x{sheet.height})")


if __name__ == "__main__":
    main()
