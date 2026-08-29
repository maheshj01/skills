---
name: flutter-diagnose-jank
description: >-
  Diagnose and verify Flutter UI performance (jank, stutter, dropped frames,
  scroll/swipe/animation smoothness) with measured frame timings instead of
  guesswork. Use whenever the user says a screen "isn't smooth", "stutters",
  "lags", "feels janky", drops frames, or asks to profile/verify performance or
  prove a screen renders at 60/90/120fps — even if they don't say the word
  "jank". Follows a classify-first method: find which pipeline stage
  (Build/Layout/Paint/Raster) blows the frame budget, fix that stage, then prove
  it with before/after numbers captured from the Dart VM Service.
metadata:
  last_modified: Thu, 28 Aug 2026 00:00:00 GMT
---
# Diagnosing Flutter jank, measure-first

## The core principle: classify before you optimize

Every frame is a pipeline: **Build → Layout → Paint (record) → Raster (GPU)**.
A janky frame is slow in exactly one of those stages, and the fix for each is
completely different. The most common and expensive mistake is guessing at a fix
before knowing which stage is over budget. So the first move is always to
**measure and classify**, never to start optimizing.

Two numbers decide everything:
- The **frame budget** = 1000 / refresh rate. 60Hz → 16.7ms, 90Hz → 11.1ms,
  120Hz → 8.3ms. Always use the device's *actual* refresh rate.
- The **widest stage** in the janky frame. That names the problem.

## Workflow

### 1. Reproduce in profile mode (never debug)
Debug mode has no JIT optimization and adds asserts; its numbers are meaningless
(the on-device banner says exactly this). Measure on a real device or profile
build:
```bash
flutter run --profile -d <device-id>
```
`flutter run` prints a **VM Service** URL like
`http://127.0.0.1:60625/Jn_CXKzvLNk=` — keep it; the scripts need it.

### 2. Capture frame timings around the janky gesture
Use the bundled harness so the gesture is *repeatable* (a scripted swipe, not a
varying thumb) and the result is an objective table:
```bash
scripts/capture_timeline.sh \
  --vm  <vm-service-url> \
  --device <device-id> \
  --gesture swipe-lr   # swipe-lr | swipe-ud | tap-cycle
```
This clears the timeline, drives the gesture, pulls `getVMTimeline`, and prints a
per-stage table (p50/p90/p99/max + jank count vs the auto-detected refresh rate).

If you already have a timeline dump, parse it directly:
```bash
python3 scripts/measure_frames.py timeline.json          # human table
python3 scripts/measure_frames.py timeline.json --json    # machine-readable
```
Exit code is non-zero when any frame exceeds budget, so it can gate a check.

Prefer this over eyeballing DevTools when you want a number to compare against.
DevTools → Performance (Flutter frames chart, Frame Analysis, Timeline Events)
is the interactive equivalent and is great for a first look; press `P` in the
`flutter run` console to toggle the live performance overlay.

### 3. Classify and fix
Read the widest stage from the table, then open the relevant code with that
stage in mind. **`references/paint-cost-checklist.md`** maps each stage to its
usual causes and fixes — read it before proposing a change. In short:
- Wide **BUILD** → too-broad/too-frequent rebuilds (e.g. a controller built in
  `build()`); check DevTools "Track Widget Builds".
- Wide **LAYOUT** → intrinsic sizing, non-lazy long lists.
- Wide **LayerTree::Paint** → an expensive `CustomPainter` (per-item
  `TextPainter.layout()`, no raster cache, broken `shouldRepaint`).
- Wide **GPURasterizer::Draw** → `saveLayer`, shadows/blurs, big images.

### 4. Prove it with before/after numbers
Capture, apply the fix, capture again, and show the widest stage dropping below
budget. Don't report "feels smoother" — report the delta. For painter fixes the
cleanest signal is **`LayerTree::Paint` collapsing to ~0.1ms**, which proves the
painter is now raster-cached and no longer runs per frame.

## Notes and gotchas
- The VM Service HTTP GET interface mangles array RPC params, so
  `setVMTimelineFlags` may reject them. You usually don't need it: profile builds
  record the Embedder stream (frame events) by default, so `clearVMTimeline` +
  gesture + `getVMTimeline` is enough. If events are missing, enable streams from
  DevTools → Performance.
- Swipe coordinates in `capture_timeline.sh` assume a 1080-wide screen. Check
  `adb -s <device> shell wm size` and adjust if needed.
- iOS simulators can't run profile mode (needs a physical iOS device); Android
  emulators can. Match the device class the user actually ships on when possible.
- Keep the fix scoped to the stage you measured. If Paint was the problem, a
  rebuild optimization is noise — and vice versa.
