#!/usr/bin/env python3
"""
video_report.py

Scans a target folder recursively and produces two reports:
- CSV
- TSV

Output filenames include the scanned folder name + probe datetime:
  video_check_<foldername>_<YYYY-MM-DD_HHMM>.csv
  video_check_<foldername>_<YYYY-MM-DD_HHMM>.tsv

Run (example):
  python3 video_report.py /path/to/folder

Requires:
  ffprobe (from FFmpeg)
"""

import argparse
import csv
import json
import subprocess
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from typing import Dict, Any, List, Optional


EXTS = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm", ".flv", ".wmv"}


def run(cmd: List[str]) -> str:
    return subprocess.check_output(cmd, text=True, errors="replace")


def frac_to_float(s: str) -> Optional[float]:
    try:
        return float(Fraction(s))
    except Exception:
        return None


def ffprobe_json(path: str) -> Dict[str, Any]:
    return json.loads(
        run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path])
    )


def ffprobe_info(path: str) -> Dict[str, Any]:
    data = ffprobe_json(path)

    vstreams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
    v = vstreams[0] if vstreams else {}
    fmt = data.get("format", {}) or {}

    width = v.get("width")
    height = v.get("height")

    sar = v.get("sample_aspect_ratio") or ""
    dar = v.get("display_aspect_ratio") or ""

    rfr = v.get("r_frame_rate") or ""
    afr = v.get("avg_frame_rate") or ""
    fps_val = frac_to_float(afr) or frac_to_float(rfr) or 0.0

    dur = v.get("duration") or fmt.get("duration") or ""
    try:
        duration = float(dur)
    except Exception:
        duration = 0.0

    nb = v.get("nb_frames")
    frames: Any = ""
    if nb and nb != "N/A":
        try:
            frames = int(nb)
        except Exception:
            frames = ""
    elif fps_val and duration:
        frames = int(round(duration * fps_val))

    st = v.get("start_time") or fmt.get("start_time") or 0.0
    try:
        start_time = float(st)
    except Exception:
        start_time = 0.0

    return {
        "WxH": f"{width}x{height}" if width and height else "",
        "FPS": f"{fps_val:.3f}" if fps_val else "",
        "Frames": frames,
        "DurationSeconds": f"{duration:.6f}" if duration else "",
        "SAR": sar if sar != "N/A" else "",
        "DAR": dar if dar != "N/A" else "",
        "StartSeconds": f"{start_time:.6f}",
    }


def keyframe_summary(path: str) -> Dict[str, Any]:
    try:
        out = run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-skip_frame",
                "nokey",
                "-show_entries",
                "frame=best_effort_timestamp_time",
                "-of",
                "default=nw=1:nk=1",
                path,
            ]
        ).splitlines()

        ts = [float(x) for x in out if x.strip()]
        keyframes = len(ts)

        if keyframes < 2:
            return {"Keyframes": keyframes, "KF_Min_s": "", "KF_Avg_s": "", "KF_Max_s": ""}

        d = [b - a for a, b in zip(ts, ts[1:])]
        kmin = min(d)
        kmax = max(d)
        kavg = sum(d) / len(d)

        return {
            "Keyframes": keyframes,
            "KF_Min_s": f"{kmin:.3f}",
            "KF_Avg_s": f"{kavg:.3f}",
            "KF_Max_s": f"{kmax:.3f}",
        }
    except Exception:
        return {"Keyframes": "", "KF_Min_s": "", "KF_Avg_s": "", "KF_Max_s": ""}


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("folder", help="Folder to scan recursively")
    ap.add_argument("--outdir", default=".", help="Where to write the CSV/TSV (default: current directory)")
    args = ap.parse_args()

    root = Path(args.folder).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Folder not found or not a directory: {root}")

    outdir = Path(args.outdir).expanduser().resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    folder_name = root.name
    probe_dt = datetime.now().strftime("%Y-%m-%d_%H%M")
    probe_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    csv_path = outdir / f"video_check_{folder_name}_{probe_dt}.csv"
    tsv_path = outdir / f"video_check_{folder_name}_{probe_dt}.tsv"

    fields = [
        "Folder",
        "ProbeDate",
        "File",
        "WxH",
        "FPS",
        "Frames",
        "DurationSeconds",
        "SAR",
        "DAR",
        "StartSeconds",
        "Keyframes",
        "KF_Min_s",
        "KF_Avg_s",
        "KF_Max_s",
    ]

    rows: List[Dict[str, Any]] = []

    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix.lower() not in EXTS:
            continue

        rel = p.relative_to(root).as_posix()
        info = ffprobe_info(str(p))
        kf = keyframe_summary(str(p))

        row = {
            "Folder": folder_name,
            "ProbeDate": probe_iso,
            "File": rel,
            **info,
            **kf,
        }
        rows.append(row)

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    with tsv_path.open("w", newline="", encoding="utf-8") as f:
        f.write("\t".join(fields) + "\n")
        for r in rows:
            f.write("\t".join(str(r.get(k, "")) for k in fields) + "\n")

    print(str(csv_path))
    print(str(tsv_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
