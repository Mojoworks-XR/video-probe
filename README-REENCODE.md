# reencode_for_sync.zsh

Re-encodes a folder of videos into a new folder with **sync-friendly** settings (constant frame rate + regular keyframes), while keeping **high visual quality**.  
Original files are **not modified**.

## What it does

For every video found under the input folder (recursively):

1. **Finds video files recursively**  
   Scans for: `.mp4 .mov .m4v .mkv .avi .webm .flv .wmv`

2. **Writes outputs into a separate folder**  
   Creates the same subfolder structure under the output directory and writes an `.mp4` file there.

3. **Forces consistent playback timing**
   - Reads the source FPS via `ffprobe`
   - Re-encodes with **constant frame rate** (CFR) at that FPS
   - Computes a GOP size so keyframes occur every **N seconds** (default **2.0s**)
   - Forces keyframes at exactly regular intervals (0s, N s, 2N s, …)
   - Disables scene-cut keyframes (so keyframes don’t “move around” between files)

4. **Re-encodes video to H.264 (MP4) at high quality**
   - Codec: H.264 (`libx264`)
   - Quality: `CRF 16` (high quality, still lossy)
   - Speed/quality tradeoff: `preset slow`
   - Pixel format: `yuv420p`
   - Profile/level: `high@4.1`
   - Fast start enabled (`+faststart`) for better streaming/players

5. **Handles audio safely**
   - If audio exists: re-encodes to **AAC 192 kbps**, stereo, 48 kHz
   - If audio does not exist: outputs **video-only** (no audio track)

6. **Does not overwrite originals**
   - All outputs go into the output folder you specify
   - If an output file already exists and is newer than the source, it is **skipped**

7. **Creates a log**
   - Writes ffmpeg output to: `OUT_ROOT/encode.log`
   - Prints a per-file summary to the terminal

## Why this is useful for sync

When multiple screens/devices need to start/loop together, inconsistency in timing and keyframe placement can make one screen “catch” slightly differently than another. This script makes the files structurally more consistent by using:
- constant frame rate
- fixed keyframe cadence
- forced keyframes at known times

## Requirements

- macOS with Zsh (default on modern macOS)
- FFmpeg/ffprobe installed:
  ```bash
  brew install ffmpeg
  ```

## How to run

1. Make it executable:

   ```bash
   chmod +x reencode_for_sync.zsh
   ```

2. Run it:

   ```bash
   ./reencode_for_sync.zsh [IN_ROOT] [OUT_ROOT] [KEYFRAME_INTERVAL_SECONDS]
   ```

### Examples

Re-encode everything in the current folder into `reencoded/` with keyframes every 2 seconds:

```bash
./reencode_for_sync.zsh . reencoded 2.0
```

Re-encode a specific folder:

```bash
./reencode_for_sync.zsh "/path/to/input" "/path/to/output" 1.0
```

## Output

* Re-encoded videos: `OUT_ROOT/<same subfolders>/<same name>.mp4`
* Log file: `OUT_ROOT/encode.log`

Terminal summary at the end:

* total files found
* successfully encoded
* skipped (already up-to-date)
* failed (see log)

## Notes / limitations

* Re-encoding H.264 is **always lossy** (even at high quality). CRF 16 is typically visually very close to the source.
* If a source is 10-bit or 4:2:2, this script outputs 8-bit 4:2:0 (`yuv420p`). That’s often best for player compatibility.
* Keyframe interval can be changed via the 3rd argument (e.g. `1.0` for every 1 second).
