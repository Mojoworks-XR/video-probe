#!/usr/bin/env zsh
# reencode_for_sync.zsh
#
# What it does (plain English):
# - Finds all video files under IN_ROOT (recursively).
# - For each file, creates an output path under OUT_ROOT, preserving subfolders.
# - Re-encodes to MP4 (H.264) with:
#     - constant frame rate (matches source FPS)
#     - forced keyframes at a regular interval (default 2.0 seconds)
#     - no extra “scene cut” keyframes (keeps cadence consistent)
#     - high quality settings (CRF 16, preset slow)
# - If audio exists, it re-encodes audio to AAC 192k; if no audio, outputs video-only.
# - Originals are untouched. Outputs go to OUT_ROOT.
#
# Usage:
#   chmod +x reencode_for_sync.zsh
#   ./reencode_for_sync.zsh [IN_ROOT] [OUT_ROOT] [KEYFRAME_INTERVAL_SECONDS]
#
# Example:
#   ./reencode_for_sync.zsh . reencoded 2.0
#
# Requirements:
#   brew install ffmpeg

set -uo pipefail
setopt nullglob

IN_ROOT="${1:-.}"
OUT_ROOT="${2:-reencoded}"
KSECS="${3:-2.0}"

mkdir -p "$OUT_ROOT"
LOG="$OUT_ROOT/encode.log"
: > "$LOG"

echo "IN_ROOT : $IN_ROOT"
echo "OUT_ROOT: $OUT_ROOT"
echo "KF every: ${KSECS}s"
echo "LOG     : $LOG"
echo

# Build find expression
find_cmd=(find "$IN_ROOT" -type f \( \
  -iname "*.mp4" -o -iname "*.mov" -o -iname "*.m4v" -o -iname "*.mkv" -o -iname "*.avi" -o -iname "*.webm" -o -iname "*.flv" -o -iname "*.wmv" \
\) -print0)

total=0
ok=0
fail=0
skip=0

# IMPORTANT: process substitution avoids piping into the loop (ffmpeg won't steal stdin)
while IFS= read -r -d '' f; do
  (( total++ ))

  # Make a clean relative path (works for IN_ROOT="." too)
  f_clean="${f#./}"
  root_clean="${IN_ROOT%/}"
  root_clean="${root_clean#./}"

  if [[ "$root_clean" == "" || "$root_clean" == "." ]]; then
    rel="$f_clean"
  else
    rel="${f_clean#${root_clean}/}"
  fi

  # Output path: preserve subfolders, force .mp4 extension
  out="$OUT_ROOT/$rel"
  out="${out%.*}.mp4"
  outdir="${out:h}"
  mkdir -p "$outdir"

  # Skip if output exists and is newer
  if [[ -f "$out" && "$out" -nt "$f" ]]; then
    echo "[$total] SKIP (newer output exists): $rel"
    (( skip++ ))
    continue
  fi

  # Probe FPS
  fps_frac="$(ffprobe -v error -select_streams v:0 \
    -show_entries stream=avg_frame_rate -of default=nw=1:nk=1 -- "$f" | tr -d '\r')"

  pair="$(python3 - "$fps_frac" "$KSECS" <<'PY'
from fractions import Fraction
import sys
fps_s=(sys.argv[1] or "").strip()
ksecs=float(sys.argv[2])
try:
    fps=float(Fraction(fps_s))
except Exception:
    fps=24.0
gop=max(1,int(round(fps*ksecs)))
if gop > 300: gop = 300
print(f"{fps:.6f} {gop}")
PY
)"
  fps_float="${pair%% *}"
  gop="${pair##* }"

  # Probe dimensions + duration (for logging)
  meta="$(ffprobe -v error -select_streams v:0 \
    -show_entries stream=width,height:format=duration \
    -of default=nw=1 -- "$f" 2>/dev/null | tr '\n' ' ')"

  # Audio present?
  has_audio="$(ffprobe -v error -select_streams a \
    -show_entries stream=index -of default=nw=1:nk=1 -- "$f" | head -n 1 | tr -d '\r')"

  echo "[$total] ENCODE: $rel"
  echo "     src: $meta"
  echo "     fps: $fps_float   gop: $gop (~${KSECS}s keyframes)"
  echo "     out: ${out#./}"
  echo "----------------------------------------"

  # Build ffmpeg args (no stdin; no interactive; safe inside loops)
  args=()
  args+=(-hide_banner -nostdin -y -loglevel error)
  args+=(-i "$f")
  args+=(-map 0:v:0)

  if [[ -n "$has_audio" ]]; then
    args+=(-map '0:a?')
  else
    args+=(-an)
  fi

  args+=(-c:v libx264 -preset slow -crf 16)
  args+=(-pix_fmt yuv420p -profile:v high -level:v 4.1)
  args+=(-movflags +faststart)
  args+=(-fps_mode cfr -r "$fps_float")
  args+=(-g "$gop" -keyint_min "$gop" -sc_threshold 0)
  args+=(-force_key_frames "expr:gte(t,n_forced*${KSECS})")

  if [[ -n "$has_audio" ]]; then
    args+=(-c:a aac -b:a 192k -ac 2 -ar 48000)
  fi

  args+=("$out")

  # Run encode (stdin redirected so ffmpeg cannot prompt)
  if ffmpeg "${args[@]}" < /dev/null >>"$LOG" 2>&1; then
    echo "     OK"
    echo
    (( ok++ ))
  else
    echo "     FAIL (see $LOG)"
    echo
    rm -f "$out" 2>/dev/null || true
    (( fail++ ))
  fi

done < <("${find_cmd[@]}")

echo "DONE"
echo "  total: $total"
echo "  ok   : $ok"
echo "  skip : $skip"
echo "  fail : $fail"
echo "  log  : $LOG"
