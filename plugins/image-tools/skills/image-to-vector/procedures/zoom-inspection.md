# Zoom Inspection

## Purpose

Inspect details that may look correct at normal size but fail under close review — especially for logos, icons, app assets, and small UI graphics.

Use this after initial render comparison and before final delivery when the image has important curves, corners, counters, narrow gaps, gradients, or small details.

## Procedure

1. Create enlarged views or crops around important detail areas.
2. Compare each source crop against the rendered vector crop.
3. Apply the relevant criteria.
4. Fix visible mismatches.
5. Re-render and confirm the fix still looks correct at intended display size.

## Zoom Areas

Inspect crops around:

- curve-to-line transitions
- inside and outside corners
- sharp points and rounded corners
- joins, intersections, and line terminals
- holes, counters, cutouts, and narrow gaps
- small decorative details
- color or gradient boundaries
- areas where tracing introduced noise or simplification

## Zoom Levels

Use practical enlarged sizes:

- 2x for general shape issues
- 4x for curves, joins, and corners
- 8x or higher for small icons, tight gaps, and transition points

Do not judge from zoom alone — the final result must still look correct at the intended display size.

## Criteria References

During zoom inspection, apply:

- `criteria/geometry.md`
- `criteria/color.md`
- `criteria/gradients.md`

For overall pass/fail and the rules against hiding errors or overfitting crops, see `criteria/visual-fidelity.md`.

## Common Zoom Defects

Look for avoidable:

- faceted or lumpy curves
- incorrect corner sharpness
- shifted transition points
- broken joins, gaps, overlaps, or clipped endpoints
- collapsed holes/counters or distorted negative space
- uneven stroke or shape weight
- stray tracing fragments or color islands
- misplaced gradient edges or highlights
- **missing kink** — single curve where the inventory has a corner
- **smoothed spike** — smooth bend where the inventory has a V-notch
- **contour-direction reversal smoothed across** — Bézier bridged over a spike
- **phantom notch** — V-notch where the inventory has only a smooth/corner vertex

Definitions of the inventory-conformance failure modes live in
`criteria/geometry.md`.
