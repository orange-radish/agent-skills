# Inspect Source

## Purpose

Build a feature inventory from the raster *before* any path commands are
written. This step exists so corners, slope-breaks, spikes, and stripped
visual effects are committed to in writing before authoring.

No path commands are authored until a segment plan
(`procedures/segment-plan.md`) is filled out from this inventory.

## Setup

```sh
python3 -c "import PIL, numpy"
```

If that errors, install from `tools/requirements.txt`:

```sh
python3 -m pip install -r tools/requirements.txt
```

## Run

```sh
python3 tools/inspect-outline.py "$SOURCE" \
  --out /tmp/inventory.json \
  --render-overlay /tmp/inventory-overlay.png
```

Always render the overlay. Look at it before trusting the JSON.

## Verify the overlay

Open `/tmp/inventory-overlay.png`. Confirm:

- The simplified contour follows the *underlying icon edge*, not a glow
  envelope, drop shadow, or blur halo.
- Marked vertices (yellow=smooth, orange=corner, red=sharp_corner,
  magenta=spike) line up with visible structural features in the source.
- The number of `corner`/`sharp_corner`/`spike` vertices is plausible —
  not dominated by anti-alias jitter.

If the contour rides the glow instead of the icon, the `effects_detected`
field will name the effect. Re-run with `--strip-effects auto` (the
default) or with a tighter `--rdp-epsilon` (try `1.5`–`2.5`) if the
overlay has noise corners. If the contour is missing real structure,
loosen `--rdp-epsilon` (try `0.5`–`1.0`).

For a glow / drop shadow / colored halo source, expect `effects_detected`
to be non-empty.

## Read the JSON

Each contour ships `vertices` and `segments`. Cross-reference each `spike`
and `sharp_corner` vertex with the source — these are the structural
features that must survive into the authored path (see
`criteria/geometry.md`).

`segments[].kind ∈ {line, arc, curve_freeform, spike_reversal}` is the
authoring contract. The segment plan binds each row of the plan to one
of these kinds.

## Commit to a segment plan

Open `procedures/segment-plan.md` and fill out the table for every
segment in the inventory. Then move to `procedures/vtracer-first-pass.md`.
