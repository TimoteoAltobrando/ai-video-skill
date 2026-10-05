#!/usr/bin/env python3
"""Inventory of a folder of footage: one row per clip, and optionally one contact sheet per clip.
Usage:
  python3 inventory.py footage/original --out docs/footage.md [--sheets docs/sheets] [--every 5] [--scenes 0.35]
It reads every video file (mov, mp4, m4v, mkv, webm, avi, mts) with ffprobe and writes a markdown table: file, duration,
size, frame rate (and VFR when the rate is variable, common on phones), codec, HDR (HLG / PQ), rotation, audio, date.
--sheets  writes <name>.jpg for each clip: one frame every --every seconds, in a grid with the time in the corner.
          Look at them before choosing anything: they are how you "watch" hours of footage.
--scenes  also counts the cuts or big changes inside each clip (ffmpeg scene score above the threshold); useful to
          find the shots inside a long recording that was already edited.
The originals are only read, never changed.
Needs ffmpeg/ffprobe, and Pillow for --sheets.
"""
import argparse
import json
import pathlib
import subprocess
import tempfile

EXT = {".mov", ".mp4", ".m4v", ".mkv", ".webm", ".avi", ".mts"}


def probe(p: pathlib.Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(p)],
                       capture_output=True, text=True)
    return json.loads(r.stdout or "{}")


def rate(s: str) -> float:
    n, _, d = (s or "0/1").partition("/")
    return float(n) / float(d or 1) if float(d or 1) else 0.0


def rotation(v: dict) -> int:
    for sd in v.get("side_data_list") or []:
        if "rotation" in sd:
            return int(sd["rotation"])
    return int((v.get("tags") or {}).get("rotate", 0))


def scenes(p: pathlib.Path, threshold: float) -> int:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(p), "-vf",
                        f"scale=320:-2,select='gt(scene,{threshold})',showinfo", "-an", "-f", "null", "-"],
                       capture_output=True, text=True)
    return r.stderr.count("pts_time:")


def sheet(p: pathlib.Path, out: pathlib.Path, every: float) -> None:
    from PIL import Image, ImageDraw
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-vf", f"fps=1/{every},scale=320:-2",
                        f"{tmp}/f%05d.png"], check=True)
        frames = sorted(pathlib.Path(tmp).glob("f*.png"))
        if not frames:
            return
        w, h = Image.open(frames[0]).size
        cols = min(6, len(frames))
        rows = (len(frames) + cols - 1) // cols
        grid = Image.new("RGB", (cols * (w + 4) + 4, rows * (h + 4) + 4), "black")
        for i, f in enumerate(frames):
            im = Image.open(f).convert("RGB")
            t = int(i * every)
            ImageDraw.Draw(im).text((6, 4), f"{t // 3600}:{t // 60 % 60:02d}:{t % 60:02d}", fill="white",
                                    stroke_width=2, stroke_fill="black")
            grid.paste(im, (4 + (i % cols) * (w + 4), 4 + (i // cols) * (h + 4)))
        grid.save(out, quality=85)


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("folder")
    a.add_argument("--out", required=True)
    a.add_argument("--sheets")
    a.add_argument("--every", type=float, default=5.0)
    a.add_argument("--scenes", type=float)
    x = a.parse_args()
    files = sorted(f for f in pathlib.Path(x.folder).rglob("*") if f.suffix.lower() in EXT and f.is_file())
    if not files:
        raise SystemExit(f"no video files in {x.folder}")
    if x.sheets:
        pathlib.Path(x.sheets).mkdir(parents=True, exist_ok=True)
    head = "| File | Duration | Size | fps | Codec | HDR | Rotation | Audio | Date |" + (" Cuts |" if x.scenes else "")
    rows = [head, "|" + "---|" * (head.count("|") - 1)]
    total = 0.0
    for f in files:
        info = probe(f)
        v = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
        if not v:
            continue
        au = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)
        dur = float(info.get("format", {}).get("duration", 0))
        total += dur
        fr, avg = rate(v.get("r_frame_rate")), rate(v.get("avg_frame_rate"))
        fps = f"{avg:.2f}" + (" VFR" if fr and avg and abs(fr - avg) > 0.05 else "")
        trc = v.get("color_transfer", "")
        hdr = {"arib-std-b67": "HLG", "smpte2084": "PQ"}.get(trc, "no")
        date = ((info.get("format", {}).get("tags") or {}).get("creation_time", "") or "")[:16].replace("T", " ")
        audio = f"{au.get('codec_name')} {au.get('channels')}ch" if au else "none"
        m, s = divmod(dur, 60)
        row = (f"| {f.relative_to(x.folder)} | {int(m)}:{s:04.1f} | {v.get('width')}×{v.get('height')} | {fps} | "
               f"{v.get('codec_name')} {v.get('pix_fmt', '')} | {hdr} | {rotation(v)} | {audio} | {date} |")
        if x.scenes:
            row += f" {scenes(f, x.scenes)} |"
        rows.append(row)
        if x.sheets:
            sheet(f, pathlib.Path(x.sheets) / f"{f.stem}.jpg", x.every)
        print(f"ok {f.name}")
    m, s = divmod(total, 60)
    rows += ["", f"{len(rows) - 2} clips, {int(m // 60)} h {int(m % 60)} min {int(s)} s in total."]
    pathlib.Path(x.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(x.out).write_text("\n".join(rows) + "\n")
    print(f"-> {x.out}")


if __name__ == "__main__":
    main()
