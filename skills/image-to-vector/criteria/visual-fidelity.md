# Visual Fidelity Criteria

## Purpose

This file is the central reference for what "visually matches the source" means. It defines the source of truth, the core rules referenced from all procedure and output files, the pass/fail standard, and the final approval checklist.

The vector should preserve the intended design, not raster noise, compression artifacts, or accidental antialiasing.

## Source of Truth

The source raster image is the visual source of truth.

If a reviewed SVG is created, it is an intermediate. It must first be validated against the source raster before it is used to judge other outputs. If the SVG and the raster disagree, the raster wins.

## Core Rules

These rules apply at every stage. Procedure and output files reference this section instead of restating them.

- Do not approve output from path data, code, or markup alone — render and compare.
- Do not hide mismatches with padding, scaling, clipping, or background changes.
- Do not optimize or simplify paths before visual correctness is achieved.
- Do not embed or preserve raster pixels as the "vector" output.
- Do not preserve raster noise as vector detail.
- Do not silently drop gradients, opacity, holes, counters, strokes, or color regions.
- Do not eyeball pixel coordinates from a render or screenshot — use vtracer or original source path data.

## Required Comparison Views

Inspect the source and rendered vector in:

- side-by-side at original size
- side-by-side at 2x or 4x
- overlay or difference view, if available
- zoom crops of important transition points

## Pass / Fail Standard

The pass/fail standard is **every applicable file in this directory**:

- `criteria/geometry.md`
- `criteria/color.md`
- `criteria/gradients.md`
- the rules and approval checklist in this file

The output passes only if every applicable criterion is satisfied. As a second order check, a normal viewer should recognize the result as the same design, and a careful viewer should not notice avoidable errors.

The numerical pixel-difference metric (see `procedures/render-compare-iterate.md`) is one supplementary signal — useful for surfacing violations during inspection. A low diff number does **not** excuse a criterion violation, and a high number that turns out to be antialiasing noise does not by itself fail the output. Use it alongside the criteria, not instead of them.

If uncertainty remains, continue inspecting or state the uncertainty explicitly.

## Approval Checklist

Before final delivery, confirm:

- [ ] The source raster was inspected.
- [ ] Reviewed SVG was rendered and compared to the source.
- [ ] Each requested output was rendered or previewed.
- [ ] Each requested output was compared against the source raster.
- [ ] If a reviewed SVG was used, requested outputs were also compared against it.
- [ ] Output was inspected at original and enlarged size.
- [ ] Important transition points were zoom-inspected.
- [ ] Silhouette, proportions, internal shapes, and negative space match.
- [ ] Curves, angles, corners, joins, and terminals are accurate.
- [ ] Stroke or shape weight is preserved.
- [ ] Flat colors are visually correct.
- [ ] Gradients are preserved or documented.
- [ ] No embedded raster image remains.
- [ ] No obvious tracing noise remains.

## Acceptable Approximation

Approximation is acceptable only when:

- the source is low-resolution or ambiguous
- the requested style allows simplification
- the target format cannot represent the feature exactly
- the approximation is visually equivalent at intended display size

When approximation is used, document:

- what was approximated
- why
- whether the difference is visible
