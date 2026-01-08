# Requires: brew install ffmpeg
#!/usr/bin/env python3
import csv, json, subprocess
from pathlib import Path
from fractions import Fraction

EXTS = {".mp4",".mov",".m4v",".mkv",".avi",".webm",".flv",".wmv"}

def run(cmd):
    return subprocess.check_output(cmd, text=True, errors="replace")

def frac_to_float(s):
    try:
        f = Fraction(s)
        return float(f)
    except Exception:
        return None

def ffprobe_info(path: str):
    j = run(["ffprobe","-v","error","-print_format","json","-show_format","-show_streams", path])
    data = json.loads(j)

    vstreams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
    v = vstreams[0] if vstreams else {}

    fmt = data.get("format", {}) or {}

    width  = v.get("width")
    height = v.get("height")

    sar = v.get("sample_aspect_ratio") or ""
    dar = v.get("display_aspect_ratio") or ""

    rfr = v.get("r_frame_rate") or ""
    afr = v.get("avg_frame_rate") or ""
    fps = frac_to_float(afr) or frac_to_float(rfr) or 0.0

    dur = v.get("duration") or fmt.get("duration") or ""
    try:
        duration = float(dur)
    except Exception:
        duration = 0.0

    nb = v.get("nb_frames")
    frames = ""
    if nb and nb != "N/A":
        try:
            frames = int(nb)
        except Exception:
            frames = ""
    elif fps and duration:
        frames = int(round(duration * fps))

    st = v.get("start_time") or fmt.get("start_time") or 0.0
    try:
        start_time = float(st)
    except Exception:
        start_time = 0.0

    return {
        "File": path,
        "WxH": f"{width}x{height}" if width and height else "",
        "FPS": f"{fps:.3f}" if fps else "",
        "Frames": frames,
        "DurationSeconds": f"{duration:.6f}" if duration else "",
        "SAR": sar,
        "DAR": dar,
        "StartSeconds": f"{start_time:.6f}",
    }

def keyframe_summary(path: str):
    # Keyframes (count + min/avg/max interval). Safe: blank if probe fails.
    try:
        out = run([
            "ffprobe","-v","error","-select_streams","v:0","-skip_frame","nokey",
            "-show_entries","frame=best_effort_timestamp_time",
            "-of","default=nw=1:nk=1", path
        ]).splitlines()
        ts = [float(x) for x in out if x.strip()]
        if len(ts) < 2:
            return {"Keyframes": len(ts), "KF_Min_s":"", "KF_Avg_s":"", "KF_Max_s":""}
        d = [b-a for a,b in zip(ts, ts[1:])]
        return {
            "Keyframes": len(ts),
            "KF_Min_s": f"{min(d):.3f}",
            "KF_Avg_s": f"{(sum(d)/len(d)):.3f}",
            "KF_Max_s": f"{max(d):.3f}",
        }
    except Exception:
        return {"Keyframes":"", "KF_Min_s":"", "KF_Avg_s":"", "KF_Max_s":""}

rows = []
for p in sorted(Path(".").rglob("*")):
    if p.is_file() and p.suffix.lower() in EXTS:
        info = ffprobe_info(str(p))
        info.update(keyframe_summary(str(p)))
        rows.append(info)

fields = ["File","WxH","FPS","Frames","DurationSeconds","SAR","DAR","StartSeconds","Keyframes","KF_Min_s","KF_Avg_s","KF_Max_s"]

# Write CSV + TSV
with open("video_check_report.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

with open("video_check_report.tsv", "w", newline="", encoding="utf-8") as f:
    f.write("\t".join(fields) + "\n")
    for r in rows:
        f.write("\t".join(str(r.get(k,"")) for k in fields) + "\n")

print("Wrote: video_check_report.csv")
print("Wrote: video_check_report.tsv")

