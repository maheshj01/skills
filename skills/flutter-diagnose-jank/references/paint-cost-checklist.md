# Which stage is slow → what to look for

The timeline names the guilty stage. Match it here, then inspect the code for
the listed causes. Fixing the wrong stage wastes effort — a rebuild fix does
nothing for a raster-bound frame.

## Wide BUILD (UI thread)
The widget tree is rebuilding too much or too expensively.
- A controller/animation/object constructed **inside `build()`** instead of
  `initState` — it's recreated every frame and can interrupt gestures. (Classic:
  `PageController(...)` in `build`.)
- `setState` called high in the tree, rebuilding large subtrees for a small change.
- Missing `const` constructors forcing rebuilds of static subtrees.
- A `Provider`/`watch` at too coarse a scope so unrelated changes rebuild the screen.
Tools: DevTools → Performance → "Rebuild Stats" / "Track Widget Builds".

## Wide LAYOUT (UI thread)
Layout is doing too much measurement.
- Intrinsic sizing (`IntrinsicHeight`/`IntrinsicWidth`) which double-walks children.
- Non-lazy lists (`Column` of hundreds) instead of `ListView.builder`.
- Deeply nested flex with unbounded constraints.

## Wide LayerTree::Paint (UI thread) — the painter tell
The paint *recording* is expensive. Almost always a `CustomPainter`.
- **Per-item allocation/work in the paint loop.** The worst offender is
  `TextPainter(...).layout()` (font shaping) called once per item per frame.
  Lay out each distinct glyph/text **once** and reuse it across items.
- **No raster cache on a static painting.** Set `isComplex: true, willChange:
  false` on `CustomPaint` so the engine caches the layer and reuse it while a
  parent scrolls/translates. After this, `LayerTree::Paint` should collapse to
  ~0.1ms because the painter stops running per frame — that collapse *is* the
  proof the fix worked.
- **`shouldRepaint` always returns true.** Often because a value object passed to
  the painter (e.g. a style/config) has no `==`/`hashCode`, so reference equality
  treats every rebuild as a change and defeats the raster cache. Add value equality.
- Over-broad `RepaintBoundary` placement, so an animating sibling forces the
  expensive painter to re-record. Wrap the expensive painter in its own
  `RepaintBoundary` to isolate it.

## Wide GPURasterizer::Draw / Rasterizer::DoDraw (raster thread)
The GPU work per frame is too heavy.
- `saveLayer` (from `Opacity` on a big subtree, blend modes, some clips) — prefer
  `AnimatedOpacity` on small leaves, or fade via color alpha in a painter.
- Shadows/blurs (`BackdropFilter`, large `BoxShadow`) — cache or simplify.
- Large or unscaled images decoded/drawn every frame — size them to their box.
- First-frame shader compilation jank — usually a one-time spike, not sustained.

## Reading the numbers
- Compare against the device's **actual** refresh rate, not a hardcoded 60Hz. A
  90Hz/120Hz screen has an 11.1ms/8.3ms budget; `measure_frames.py --hz` auto-detects.
- The most convincing check is A/B: capture, apply the fix, capture again, and
  show the widest stage dropping below budget. `LayerTree::Paint` going to ~0.1ms
  is the cleanest possible signal for painter fixes.
