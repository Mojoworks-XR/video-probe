# Video Technical Report Generator (ffprobe)

Generates a client-ready **CSV** and **TSV** report for video files in a folder **recursively** (including subfolders). The report includes **duration**, **resolution**, **fps**, **frame count**, **SAR/DAR**, **start time**, and **keyframe cadence** (keyframe count + min/avg/max interval between keyframes).

## What it outputs

Two files in the folder where the script is run:

- `video_check_report.csv` — best for emailing/attaching and opening in Excel/Sheets
- `video_check_report.tsv` — best for copy/paste into Google Sheets (tab-separated)

### Columns explained

- **File**: file path (relative to where you ran the script)
- **WxH**: pixel dimensions of the first video stream (e.g., `3840x2160`)
- **FPS**: frames per second (derived from `avg_frame_rate`, falling back to `r_frame_rate`)
- **Frames**: number of frames (`nb_frames` if available; otherwise estimated as `Duration * FPS`)
- **DurationSeconds**: duration in seconds (6 decimal places)
- **SAR**: sample aspect ratio (ideally `1:1`)
- **DAR**: display aspect ratio (e.g., `16:9`)
- **StartSeconds**: stream start time (seconds)
- **Keyframes**: number of keyframes (I-frames) detected in the first video stream
- **KF_Min_s**: smallest time gap (seconds) between consecutive keyframes
- **KF_Avg_s**: average time gap (seconds) between consecutive keyframes
- **KF_Max_s**: largest time gap (seconds) between consecutive keyframes

> Notes on keyframes:  
> The script measures **actual keyframe placement** from the file. It does not read “encoder settings” like `-g` directly (those are usually not stored explicitly), but the intervals effectively reveal the GOP/keyframe cadence.

## Requirements

- macOS
- Python 3 (usually already installed; check with `python3 --version`)
- ffprobe (installed via FFmpeg)

Install FFmpeg (includes ffprobe):

```bash
brew install ffmpeg
````

## How to run

1. Save the script as `video_report.py` (same content as provided).

2. Make it executable (optional):

```bash
chmod +x video_report.py
```

3. `cd` into the folder that contains the videos (or the parent folder of subfolders):

```bash
cd /path/to/your/video/folder
```

4. Run:

```bash
python3 video_report.py
```

(or, if executable)

```bash
./video_report.py
```

5. Collect the outputs:

* `video_check_report.csv`
* `video_check_report.tsv`

## Typical usage

### Scan a delivery folder

```bash
cd /Volumes/Deliveries/AMS_Tunnel
python3 video_report.py
```

### Open results

* macOS Finder: double-click the CSV
* Google Sheets: `File → Import → Upload` and choose the CSV/TSV

## What files are included

The script scans recursively for these extensions (case-insensitive):

`.mp4 .mov .m4v .mkv .avi .webm .flv .wmv`

## How the script works (high level)

* Walks the current directory recursively (`Path(".").rglob("*")`)
* For each video file:

  * Uses `ffprobe` JSON output to read:

    * width/height, FPS, frames, duration, SAR/DAR, start time
  * Uses `ffprobe` keyframe scan to read:

    * keyframe timestamps → computes keyframe count and min/avg/max interval
* Writes one row per file to CSV and TSV

## Troubleshooting

### “ffprobe: command not found”

FFmpeg is not installed or not on PATH:

```bash
brew install ffmpeg
```

### Empty/odd SAR or DAR

Some containers don’t set SAR/DAR explicitly; SAR should ideally be `1:1` for most modern assets.

### Frames column is blank or estimated

Some codecs/containers don’t report `nb_frames`. In that case, the script estimates frames as:
`round(DurationSeconds * FPS)`.

## License

Internal utility script — adapt as needed for deliveries and QC reports.
