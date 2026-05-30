# Segment Plan

## Purpose

The binding pre-authoring artifact. Forces structural commitment and
prevents coordinate fabrication.

A row must exist for every segment in the inventory produced by
`procedures/inspect-source.md`. No path commands are authored until this
table is filled in.

## Format

| # | from-vertex (xy) | to-vertex (xy) | kind | coord source | notes |
|---|---|---|---|---|---|

- `kind` is taken verbatim from the inventory:
  `line | arc | curve_freeform | spike_reversal`.
- `coord source` must reference one of:
  - the `inspect-outline.py` JSON path (e.g. `contours[0].vertices[3]`)
  - a vtracer SVG path command (e.g. `path[2].d, M…`)
  - an original source SVG / generator script path-data location
- Coordinates with no listed source fail the traceability rule in
  `criteria/geometry.md`.

## Authoring rule

For each row, the authored path emits exactly the matching command:

| kind | output |
|---|---|
| `line` | `addLine` / `L` |
| `arc` | `addArc` / `A` (or two-segment Bézier approximation if the target prefers) |
| `curve_freeform` | `addQuadCurve` / `addCurve` / `Q` / `C` with measured control points |
| `spike_reversal` | **two** segments meeting at the spike vertex (record coord source as `from→to, tip=<vertex>`) — never a single Bézier bridging the tip |

For decision rules on what *kind* a segment must take see
`criteria/geometry.md`. For the curvature/turn-angle thresholds that
produced the `kind` see the docstring at the top of
`tools/inspect-outline.py`.
