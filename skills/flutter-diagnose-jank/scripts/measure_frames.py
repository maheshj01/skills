#!/usr/bin/env python3
"""Parse a Dart VM Service `getVMTimeline` dump into per-stage frame stats.

The decisive question in any jank investigation is *which pipeline stage* blew
the frame budget, because each stage has a completely different fix. This script
turns a raw timeline into an objective table so "feels smoother" becomes a
measured pass/fail number.

Stages reported (Flutter engine event names):
  BUILD                 -> UI thread: widget build cost
  LAYOUT                -> UI thread: layout cost (if recorded)
  LayerTree::Paint      -> UI thread: CustomPainter/paint RECORDING cost.
                           This is the tell for painter problems: if it drops to
                           ~0.1ms after a fix, the painter is being raster-cached
                           and no longer runs per frame.
  GPURasterizer::Draw   -> Raster thread: actual GPU draw cost. The usual
                           bottleneck for shaders, saveLayer, big images.

Usage:
  python3 measure_frames.py timeline.json                 # auto-detect refresh
  python3 measure_frames.py timeline.json --hz 90         # force 90Hz budget
  python3 measure_frames.py timeline.json --json          # machine-readable

Exit code is non-zero if any janky frames were found, so it can gate CI or a
before/after check.
"""
import argparse
import collections
import json
import sys


def load_events(path):
    with open(path) as f:
        d = json.load(f)
    # getVMTimeline wraps events under result.traceEvents; a raw chrome trace
    # may put them at the top level. Handle both.
    if isinstance(d, dict):
        return d.get("result", {}).get("traceEvents", d.get("traceEvents", []))
    return d


def complete_durations(events, name):
    """Durations (us) for X-phase (complete) events of a given name."""
    return sorted(e["dur"] for e in events
                  if e.get("name") == name and e.get("ph") == "X" and "dur" in e)


def begin_end_durations(events, name):
    """Durations (us) reconstructed from matched B/E pairs per thread."""
    stacks = collections.defaultdict(list)
    out = []
    for e in sorted(events, key=lambda x: x.get("ts", 0)):
        if e.get("name") != name:
            continue
        tid = (e.get("pid"), e.get("tid"))
        if e.get("ph") == "B":
            stacks[tid].append(e["ts"])
        elif e.get("ph") == "E" and stacks[tid]:
            out.append(e["ts"] - stacks[tid].pop())
    return sorted(out)


def durations(events, name):
    return complete_durations(events, name) or begin_end_durations(events, name)


def detect_hz(events):
    """Infer refresh rate from the median gap between consecutive frame starts."""
    starts = sorted(e["ts"] for e in events
                    if e.get("name") in ("VSYNC", "Frame", "Animator::BeginFrame")
                    and "ts" in e and e.get("ph") in ("X", "B"))
    gaps = sorted(b - a for a, b in zip(starts, starts[1:]) if 0 < (b - a) < 100000)
    if not gaps:
        return 60
    median_gap = gaps[len(gaps) // 2]
    # Snap to the nearest common refresh rate.
    hz = 1_000_000 / median_gap
    for common in (120, 90, 60, 30):
        if abs(hz - common) < 8:
            return common
    return round(hz)


def pct(sorted_vals, p):
    if not sorted_vals:
        return 0
    return sorted_vals[min(len(sorted_vals) - 1, int(len(sorted_vals) * p))]


STAGES = [
    ("BUILD", "UI: widget build"),
    ("LAYOUT", "UI: layout"),
    ("LayerTree::Paint", "UI: paint record (painter cost)"),
    ("GPURasterizer::Draw", "Raster: GPU draw"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("timeline", help="path to getVMTimeline JSON dump")
    ap.add_argument("--hz", type=int, default=0, help="refresh rate; 0 = auto-detect")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args()

    events = load_events(args.timeline)
    if not events:
        print("No trace events found. Was the timeline recorded? "
              "In profile mode the Embedder stream is on by default; "
              "otherwise enable streams from DevTools > Performance.", file=sys.stderr)
        return 2

    hz = args.hz or detect_hz(events)
    budget_us = 1_000_000 / hz

    report = {"refresh_hz": hz, "budget_ms": round(budget_us / 1000, 2), "stages": {}}
    total_jank = 0
    for name, label in STAGES:
        dd = durations(events, name)
        if not dd:
            continue
        jank = sum(1 for x in dd if x > budget_us)
        total_jank += jank
        report["stages"][name] = {
            "label": label,
            "n": len(dd),
            "p50_ms": round(pct(dd, 0.50) / 1000, 2),
            "p90_ms": round(pct(dd, 0.90) / 1000, 2),
            "p99_ms": round(pct(dd, 0.99) / 1000, 2),
            "max_ms": round(max(dd) / 1000, 2),
            "jank_frames": jank,
        }
    report["total_jank_frames"] = total_jank

    if args.json:
        print(json.dumps(report, indent=2))
        return 0 if total_jank == 0 else 1

    print(f"Refresh: {hz}Hz  (budget {budget_us/1000:.1f}ms/frame)\n")
    hdr = f"{'stage':22s} {'n':>4} {'p50':>7} {'p90':>7} {'p99':>7} {'max':>8} {'jank':>5}"
    print(hdr)
    print("-" * len(hdr))
    for name, label in STAGES:
        s = report["stages"].get(name)
        if not s:
            continue
        flag = "  <-- JANK" if s["jank_frames"] else ""
        print(f"{name:22s} {s['n']:>4} {s['p50_ms']:>6}m {s['p90_ms']:>6}m "
              f"{s['p99_ms']:>6}m {s['max_ms']:>7}m {s['jank_frames']:>5}{flag}")
    print()
    if total_jank == 0:
        print(f"PASS: 0 frames exceeded the {budget_us/1000:.1f}ms budget.")
    else:
        print(f"FAIL: {total_jank} frame-stages exceeded the {budget_us/1000:.1f}ms budget.")
        print("Widest stage above = where to look. See references/paint-cost-checklist.md")
    return 0 if total_jank == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
