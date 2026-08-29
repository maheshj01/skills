#!/usr/bin/env bash
# Drive a repeatable gesture on a device and capture frame timings from the
# running app's Dart VM Service. This makes a jank check reproducible: the same
# adb swipe every time, not a thumb that varies run to run.
#
# Prerequisites:
#   - The app is already running in PROFILE mode:
#         flutter run --profile -d <device-id>
#     (Debug-mode numbers are meaningless — the on-device banner says so.)
#   - You have the VM Service base URL printed by `flutter run`, e.g.
#         http://127.0.0.1:60625/Jn_CXKzvLNk=
#   - adb is on PATH and the device id is known (`adb devices`).
#
# Usage:
#   capture_timeline.sh \
#     --vm  http://127.0.0.1:60625/Jn_CXKzvLNk= \
#     --device 192.168.0.12:5533 \
#     [--gesture swipe-lr] [--reps 10] [--out timeline.json]
#
# Gestures (coordinates are for a 1080-wide screen; tweak for your device):
#   swipe-lr   horizontal left<->right (PageView / horizontal pager)  [default]
#   swipe-ud   vertical up<->down (scroll lists)
#   tap-cycle  tap upper then lower half (tap-to-advance UIs)
set -euo pipefail

VM=""; DEVICE=""; GESTURE="swipe-lr"; REPS=10
OUT="$(dirname "$0")/../timeline.json"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --vm) VM="$2"; shift 2;;
    --device) DEVICE="$2"; shift 2;;
    --gesture) GESTURE="$2"; shift 2;;
    --reps) REPS="$2"; shift 2;;
    --out) OUT="$2"; shift 2;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done
[[ -z "$VM" || -z "$DEVICE" ]] && { echo "need --vm and --device" >&2; exit 2; }
VM="${VM%/}"  # strip trailing slash

echo "clearing timeline..."
curl -s "$VM/clearVMTimeline" >/dev/null

echo "driving '$GESTURE' x$REPS on $DEVICE..."
for _ in $(seq 1 "$REPS"); do
  case "$GESTURE" in
    swipe-lr)
      adb -s "$DEVICE" shell input swipe 950 1200 150 1200 160
      adb -s "$DEVICE" shell input swipe 150 1200 950 1200 160;;
    swipe-ud)
      adb -s "$DEVICE" shell input swipe 540 1800 540 600 160
      adb -s "$DEVICE" shell input swipe 540 600 540 1800 160;;
    tap-cycle)
      adb -s "$DEVICE" shell input tap 540 600
      adb -s "$DEVICE" shell input tap 540 1800;;
    *) echo "unknown gesture: $GESTURE" >&2; exit 2;;
  esac
done

echo "fetching timeline -> $OUT"
curl -s "$VM/getVMTimeline" -o "$OUT"

echo
python3 "$(dirname "$0")/measure_frames.py" "$OUT"
