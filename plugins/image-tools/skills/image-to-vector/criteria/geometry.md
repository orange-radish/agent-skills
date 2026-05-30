# Geometry Criteria

Check:

- silhouette
- proportions
- inner and outer contours
- line thickness
- angles
- corner sharpness
- curve smoothness
- curve-to-line transitions
- intersections
- terminals
- holes/counters
- negative space
- stroke or shape weight

## Per-segment decision rules

Source: the `inspect-outline.py` inventory drives these calls. Numeric
thresholds live in the script's docstring — do not restate them here.

- A segment is **straight** (must be authored as `addLine` / `L`) when the
  inventory classifies its `kind` as `line`. The inventory rule is
  curvature-based: low mean and max curvature along the segment.
- A segment is a **single curve** (Bézier or arc) only when the inventory
  classifies it as `arc` or `curve_freeform` — curvature is bounded and,
  for `arc`, monotone-sign.
- A vertex with `kind: corner` or `kind: sharp_corner` (turn ≥ 30°)
  separates two distinct segments. Never bridge a corner with one curve.
- A vertex with `kind: spike` (turn > 150°) is a path-direction reversal.
  The two segments meeting at a spike are authored as **two** path
  commands meeting at the spike vertex — never a single Bézier across
  the tip.

## Traceability

Every coordinate in the authored path must trace to one of:

- a `contours[].vertices[]` entry in the `inspect-outline.py` JSON
- a vtracer SVG path command
- an original source SVG / generator script / design-handoff path data

Coordinates with no listed source fail this criterion.

## Fail if

- the outline visibly changes
- curves become faceted or lumpy
- angles are visibly wrong
- holes are filled or distorted
- negative space shifts noticeably
- corners are over-smoothed
- rounded corners become angular
- endpoints are clipped or extended
- strokes become uneven

### Named structural failure modes

- **missing kink** — a single curve drawn where the inventory has a
  `corner` or `sharp_corner` vertex separating two segments.
- **smoothed spike** — a smooth bend drawn where the inventory has a
  `spike` vertex (V-notch / sharp point).
- **merged-across-reversal** — a single Bézier bridged across a
  `spike_reversal` segment instead of authored as two segments meeting
  at the spike vertex.
- **phantom notch** — a V-notch drawn where the inventory has only a
  smooth or `corner` vertex (no spike).
