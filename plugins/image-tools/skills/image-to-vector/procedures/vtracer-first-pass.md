# vtracer First Pass

## Purpose

Use `vtracer` to fill in measurements (coordinates, control points) for
the segments the feature inventory has already identified. The inventory
from `procedures/inspect-source.md` is authoritative; vtracer is a
measurement source, not a structure source. On any disagreement, the
inventory wins.

This is the first pass only — render, compare, and revise via `procedures/render-compare-iterate.md` before treating the SVG as final. Core iteration rules live in `criteria/visual-fidelity.md`.

## Inputs

- Source raster (PNG or JPEG)
- Desired vector style:
  - flat icon/logo
  - multi-color illustration
  - simple silhouette
  - detailed artwork
- Requested output format(s)

## First check that vtracer can see the subject

`--colormode bw` binarises on luminance. That separates a light subject on
a dark field, but not a mid-brightness one — a mid-green ball on navy comes
back as **nothing**: vtracer emits only the background rectangle and drops
the subject silently, with a successful exit code. Colour mode is not the
fallback; on a flat two-colour icon it returns a separate path per
antialiasing shade (dozens of them).

So look at what the trace actually contains before building anything on
it. If the subpaths do not correspond to the inventory's contours, trace a
mask instead:

```sh
python3 tools/mask-from-inventory.py inventory.json "$SOURCE" /tmp/mask.png
vtracer --input /tmp/mask.png --output /tmp/trace.svg --colormode bw --mode spline
```

That reuses the threshold `inspect-outline.py` already chose, so vtracer
and the inventory describe the same mask and their contours correspond —
worth doing even when bw mode does work.

## Run both modes and stitch by segment kind

The inventory already classified each segment. Use vtracer to measure
coordinates *per segment kind*:

- polygon-mode vertex coordinates for segments classified as `line`,
  `arc`, `sharp_corner`, or `spike` / `spike_reversal`
- spline-mode control points for segments classified as `curve_freeform`

```bash
vtracer --input "$SOURCE" --output /tmp/poly.svg   --mode polygon --filter_speckle 4 --segment_length 4
vtracer --input "$SOURCE" --output /tmp/spline.svg --mode spline  --filter_speckle 4 --segment_length 4
```

Stitch: for each segment-plan row, copy coordinates from `poly.svg` for
the polygonal kinds and from `spline.svg` for `curve_freeform`. Mode
choice is per-segment, not global.

If vtracer's segment count along a contour disagrees with the inventory,
**subdivide vtracer's path** to match the inventory. Never merge two
inventory segments to match vtracer's output — that is how kinks get
smoothed away.

### Stitching cautions

Three properties of these two tools cause silent, hard-to-spot damage when
you line an inventory segment up against vtracer's output. All three
produce plausible-looking paths, so they survive visual review.

- **The inventory and vtracer walk a contour in opposite directions.** Take
  an inventory segment's vertices in vtracer's order without checking, and
  you get the complement of the arc you wanted — the long way round the
  contour. Establish the direction **once per contour**, by checking which
  orientation makes the segment spans tile the contour exactly, and reuse
  it for every segment on that contour.

- **Do not pick the direction per segment by "shorter arc".** vtracer emits
  a fixed number of samples per cubic regardless of how long that cubic is,
  so distance in sample-index space is not proportional to arc length. A
  long segment made of few cubics can look shorter than a short segment
  made of many, and the heuristic silently selects the wrong way round —
  dropping a region's entire edge, which then fills as a solid wedge.

- **Apply each `<path>`'s `transform`.** vtracer may return its regions
  across several `<path>` elements, each carrying its own
  `transform="translate(dx,dy)"`, and the coordinates in `d` are relative
  to it. Read the `d` attributes without applying those offsets and every
  region lands somewhere wrong. This one hides easily: a trace that comes
  back as a single path at `translate(0,0)` works fine while ignoring
  transforms, so the bug only appears on a later source. Fold the offsets
  into absolute coordinates before matching anything against the
  inventory, and check the subpath count and bounding boxes against the
  inventory's contours as a cheap guard.

- **Pin each authored segment to the inventory's vertices, not to the
  nearest traced sample.** The nearest vtracer sample can sit a few px off
  the vertex the inventory named. Pin before fitting, so the fit accounts
  for it: that keeps adjacent segments sharing an exact endpoint, and keeps
  corners and spike tips as real path nodes instead of points a curve
  happens to pass near. The inventory wins on disagreement.

Verify the result rather than trusting it — see `tools/verify-conformance.py`,
described in `criteria/geometry.md`.

## Basic Command

For a quick first look before the per-segment stitch:

```bash
vtracer --input input.png --output initial.svg
```

Render and inspect the result before changing settings.

## Optional Tuning Experiments

Use these as experiments, not guaranteed presets. Change one or two settings at a time, then render and compare again.

### Hard-edged icon/logo

```bash
vtracer \
  --input "$SOURCE" \
  --output initial.svg \
  --colormode color \
  --mode polygon \
  --filter_speckle 4 \
  --color_precision 6 \
  --gradient_step 16 \
  --corner_threshold 60 \
  --segment_length 4 \
  --splice_threshold 45
```

Try this when the source is mostly flat-color, hard-edged, and geometric.

### Smooth-curve

```bash
vtracer \
  --input "$SOURCE" \
  --output initial.svg \
  --colormode color \
  --mode spline \
  --filter_speckle 4 \
  --color_precision 6 \
  --gradient_step 16 \
  --corner_threshold 60 \
  --segment_length 4 \
  --splice_threshold 45
```

Try this when smooth curves or rounded contours are visually important.

### Binary silhouette

```bash
vtracer \
  --input "$SOURCE" \
  --output initial.svg \
  --colormode bw \
  --mode spline \
  --filter_speckle 4 \
  --corner_threshold 60 \
  --segment_length 4 \
  --splice_threshold 45
```

Try this for single-color silhouettes or line-art-like inputs.

## Tuning Notes

Mode is selected per-segment (see "Run both modes and stitch by segment
kind" above), not as a global call.

- Increase `--filter_speckle` to remove small noise; decrease it if intentional small details disappear.
- Increase `--color_precision` to preserve more color distinctions; decrease it to merge near-identical colors.
- Increase `--gradient_step` to reduce color layers; decrease it to preserve subtle transitions.
- Lower `--segment_length` preserves more local detail but increases path complexity.
- Use `--hierarchical cutout` only in color mode, and only if it improves the rendered comparison.
- Check `vtracer --help` before relying on any flag.

## After Tracing

Inspect the generated SVG for:

- embedded raster images
- excessive path count
- tiny noise fragments
- jagged curves
- wrong angles
- distorted corners
- collapsed holes/counters
- incorrect fill behavior
- broken color regions
- incorrect viewBox or dimensions

Fix these via the iterate loop in `procedures/render-compare-iterate.md`. Use the priority order defined there.

## vtracer-specific Cautions

- Do not over-smooth sharp corners.
- Do not flatten intended curves into faceted line segments.

General iteration discipline (raster handling, optimization timing, hiding errors) lives in `criteria/visual-fidelity.md`.
