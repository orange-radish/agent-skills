# Render, Compare, Iterate

## Purpose

Provide the mechanics for the iterate loop: how to render the vector output, how to surface differences, and the priority order for fixing them.

The pass/fail standard is defined by the files in `criteria/` — this procedure is how you generate the views that let you check against them. The numerical pixel-diff is one signal among the criteria checks, not the standard itself.

This loop applies first to the reviewed SVG, then to each generated platform output during validation.

## Loop

Each iteration is one **render -> check -> batch-fix -> re-render** cycle. An iteration is **not** a single fix — within one iteration you should fix every unambiguous, non-interacting violation you identify. The cap on `max_iterations` bounds render-check cycles, not repairs.

Repeat until success or bailout (see "Bailout Conditions"):

1. **Render** the vector output to PNG at the source raster's dimensions.
2. **Surface differences** using as many of these views as practical:
   - side-by-side at original size and at 2x or 4x
   - overlay
   - difference image (from `magick compare`, see below)
   - zoom crops (`procedures/zoom-inspection.md`)
   - numerical pixel-diff metric
3. **Check** the render against every applicable criterion. Start with **inventory conformance**: for every vertex with `kind ∈ {corner, sharp_corner, spike}` in the `inspect-outline.py` inventory, confirm the rendered output has a visually distinct boundary at that point. A smoothed kink or smoothed spike is a `criteria/geometry.md` violation (named failure modes there). Then check `criteria/geometry.md`, `criteria/color.md`, `criteria/gradients.md`, and `criteria/visual-fidelity.md`. Record every violation with the criterion file it failed and the region of the image it affects. Use this list both to drive fixes and to detect stalled progress later.
4. **Batch-fix** every violation that is unambiguous and non-interacting. Two violations are non-interacting when fixing one does not visibly affect the other's region — e.g. a wrong color in region A and a faceted curve in region B. When violations share geometry (a control point near a corner that affects both the curve and the corner), fix one and re-check before fixing the other. Default to batching; fall back to one-at-a-time only when fixes visibly affect each other. Use the priority order in "What to Fix First" to decide what to fix first within an iteration and what to defer to a later iteration.
5. **Re-render and re-check.**

## Render Commands

For SVG:

```sh
rsvg-convert -w "$WIDTH" -h "$HEIGHT" reviewed.svg -o rendered.png

magick -background none -density 384 reviewed.svg -resize "${WIDTH}x${HEIGHT}" rendered.png
```

For SwiftUI: see `procedures/render-swiftui.md`.

For Android VectorDrawable: there is no convenient headless render. Either (a) load the XML in a small Compose preview and screenshot it, (b) export an equivalent SVG and render that as a proxy, or (c) document that direct rendering was not performed and rely on careful inspection plus consistency with the reviewed SVG.

## Diff Commands (one signal among many)

The numerical pixel-diff is **one** of the signals used during step 2 of the loop. It draws the eye to where the output differs from the source — pair it with the criteria checks. `tolerance_pct` is a noise-floor hint, not a stopping criterion: a diff under `tolerance_pct` does not by itself mean every criterion is satisfied, and a diff over `tolerance_pct` that is just antialiasing noise does not by itself fail the output.

```sh
magick compare -metric AE source.png rendered.png /tmp/diff.png

magick compare -metric MAE source.png rendered.png /tmp/diff.png

magick compare -metric PSNR source.png rendered.png /tmp/diff.png
```

`/tmp/diff.png` is a difference image — useful as a comparison view in step 2. Examine where the differences cluster and check those regions against `criteria/geometry.md`, `criteria/color.md`, and `criteria/gradients.md`.

## What to Fix First

Fix issues in this order:

1. inventory-conformance failures (missing kink, smoothed spike, merged-across-reversal, phantom notch — see `criteria/geometry.md`)
2. overall silhouette and proportions
3. major internal shapes and negative space
4. holes, counters, and cutouts
5. curves, angles, corners, joins, and terminals
6. color regions, opacity, and gradients
7. small details and tracing noise
8. path simplification and optimization

This is the canonical priority list and is referenced by `procedures/vtracer-first-pass.md`.

## Comparison Views

Use as many as practical:

- side-by-side render
- overlay
- difference view (`/tmp/diff.png` from `magick compare`)
- enlarged render
- cropped detail panels (`procedures/zoom-inspection.md`)

## Bailout Conditions

The loop exits in one of these cases:

1. **Success** — every applicable file in `criteria/` passes, enlarged inspection reveals no avoidable geometry errors, important transition points have been checked, and any unavoidable approximation is documented.
2. **Iteration cap** — `max_iterations` reached.
3. **Stalled progress** — the count of unresolved violations does not decrease for `stall_threshold` consecutive iterations (default `2`). This is a strong signal that further iterations will not help.
4. **Regression** — a fix made things visibly worse and a re-attempt did not recover. Roll back if practical; otherwise bail out.
5. **Unfixable in target format** — e.g. a radial gradient in a target that does not support one, or a stroke effect that the format cannot represent. Mark the violation as approximation-with-note. It does **not** count toward `stall_threshold` and does **not** block delivery.

For cases 2-4, **stop and hand the partial result to the user** following the Bailout Reporting format below. Do not silently approve. Do not keep iterating in the hope that more cycles will help — stalled progress is a strong signal that they will not.

For the full pass/fail standard see `criteria/visual-fidelity.md`.

## Bailout Reporting

When the loop bails out without success, surface the state to the user organized by criterion file and region. Example:

```
Bailout: stalled progress at iteration 5 of 8.

Resolved during loop:
  - geometry.md: silhouette restored, top counter cleaned up
  - color.md: background region recolored to source

Unresolved (3):
  - geometry.md, top-left: faceted curve where source is smooth (curve smoothness)
  - geometry.md, bottom-right counter: distorted negative space (holes/counters)
  - color.md, mid-canvas region A: color drifted from #2A8 to #3C9

Approximations (documented, not blocking):
  - gradients.md: radial gradient flattened to two-stop linear (target format limitation)
```

Include:

- which iteration the loop bailed out at and why (cap / stall / regression)
- which violations were resolved during the loop, so the user sees progress
- which violations are unresolved, by criterion file and region, with a guess at root cause when possible
- which violations are unavoidable approximations (separate list — these did not cause the bailout)

Do **not** describe the result as "done". Describe it as "best effort, N violations unresolved" and let the user decide whether to accept, hand-fix, or restart with different vtracer settings or a different approach.
