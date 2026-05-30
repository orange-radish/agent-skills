---
name: image-to-vector
description: Convert a raster image (PNG, JPG) into a pixel and color accurate vector format. Supports output in SVG, SwiftUI, and Android VectorDrawable XML. Use when the user wants to convert a PNG or JPG icon, logo, or illustration to SVG, SwiftUI Shape/Path/View, or Android VectorDrawable XML.
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Grep
  - Glob
---

# image-to-vector

Convert PNG or JPEG raster images into accurate vector outputs in SVG, SwiftUI, or Android VectorDrawable XML.

The workflow is **trace -> clean -> compare against criteria -> iterate**, and the iterate step is a real loop. Do not declare done until every applicable file in `criteria/` is satisfied (or remaining gaps are documented).

## Read this before you start

The biggest failure mode for this task is **failing to match the rules in `criteria/`** — `criteria/geometry.md`, `criteria/color.md`, `criteria/gradients.md`, and `criteria/visual-fidelity.md`. The criteria are the pass/fail standard. Numerical pixel-diff is one supplementary signal among many during inspection — useful for drawing your eye to where the output differs from the source, but a low diff number does **not** excuse a geometry, color, or gradient violation, and `tolerance_pct` is a noise-floor hint, not a stopping criterion. Iterate against the full set of criteria.

**Coordinate-traceability rule (hard fail).** Every numeric literal in the authored path must be traceable to one of:

- the `inspect-outline.py` JSON inventory (see `procedures/inspect-source.md`)
- a vtracer SVG path command
- an original source SVG / generator script / design-handoff path data

Coordinates with no traceable source are a geometry failure — see `criteria/geometry.md`. Do not estimate coordinates from a render or screenshot.

If the user has provided an original SVG, design source HTML, generator script, or design-handoff file, look there first. The path data in the source is canonical; vtracer and `inspect-outline.py` are how you recover structure when only a raster exists.

**Visual-effects caveat.** Glow, drop shadow, blur, and colored halos obscure the underlying geometry. `procedures/inspect-source.md` strips them and reports what was detected. Do not trace from the effect envelope.

## Setup Checks

Run once at the top:

```sh
which vtracer || echo "MISSING: vtracer - 'cargo install vtracer' (any OS), or 'brew install vtracer' on macOS"
which magick || which convert || echo "MISSING: ImageMagick - macOS: 'brew install imagemagick'; Debian/Ubuntu: 'sudo apt install imagemagick'; Fedora: 'sudo dnf install ImageMagick'; Windows: 'winget install ImageMagick.ImageMagick'"
which rsvg-convert || echo "MISSING: librsvg (provides rsvg-convert) - macOS: 'brew install librsvg'; Debian/Ubuntu: 'sudo apt install librsvg2-bin'; Fedora: 'sudo dnf install librsvg2-tools'; Windows: install via MSYS2 or conda-forge"
which swift || echo "MISSING: Swift toolchain - only required for SwiftUI output, which in practice needs macOS (SwiftUI rendering is Apple-only)"
```

Stop and ask the user to install missing tools if a required one is absent. See
the repository README "External dependencies" section for the full per-platform
install commands.

## Inputs

Required:

- source PNG or JPEG
- requested output format(s): SVG, SwiftUI, and/or Android VectorDrawable

Optional:

- exact reproduction vs simplified vector
- single-color vs multi-color
- gradient preservation
- platform sizing requirements
- project conventions or design tokens
- `tolerance_pct` - noise-floor hint for the numerical pixel-diff signal during inspection. Does **not** by itself indicate "done" — the criteria do. Default `1.5`.
- `max_iterations` - hard upper bound on the iterate loop, where one iteration is a full render -> check -> batch-fix -> re-render cycle (not a single fix). Default `8`.
- `stall_threshold` - bail out if the count of unresolved violations does not decrease for this many consecutive iterations. Default `2`.

## Workflow

### 1. Inspect the source

Follow `procedures/inspect-source.md` to produce a feature-inventory JSON
and overlay from the raster. Then check the source against
`criteria/visual-fidelity.md`, `criteria/geometry.md`, `criteria/color.md`,
and `criteria/gradients.md`.

### 2. Commit to a segment plan

Fill out the segment-plan table per `procedures/segment-plan.md`, one row
per inventory segment. No path commands are authored before the plan is
written.

### 3. First-pass trace

Run vtracer to produce an initial SVG. Follow
`procedures/vtracer-first-pass.md`. vtracer fills in coordinates and
control points for the segments the inventory already named — the
inventory wins on disagreements.

### 4. Iterate to convergence

Render the SVG, then check it against every applicable file in `criteria/` (`geometry.md`, `color.md`, `gradients.md`, `visual-fidelity.md`). Within each iteration, batch-fix every unambiguous, non-interacting violation; re-render and re-check. The numerical pixel-diff is one signal you can use during inspection (it draws your eye to where to look), but **passing every criterion is what defines "done"**, not the diff number alone.

Follow `procedures/render-compare-iterate.md` for mechanics — render commands, diff commands, the priority order for fixes, zoom inspection (`procedures/zoom-inspection.md`), and the bailout conditions (iteration cap, stalled progress, regression). On bailout, surface the partial result to the user with the violation list — do not declare done.

Cleaning the SVG is part of this loop, not a separate step.

### 5. Generate requested outputs

Generate only the requested output formats from the reviewed SVG. Do not retrace the raster for each platform unless the SVG genuinely cannot represent the target.

- For SVG: follow `outputs/svg.md`.
- For SwiftUI: follow `outputs/swiftui.md`.
- For Android VectorDrawable: follow `outputs/android-vectordrawable.md`.

### 6. Validate each generated output

For every requested output:

- Render or preview it. For SwiftUI, follow `procedures/render-swiftui.md` and feed the result back into `procedures/render-compare-iterate.md`.
- Compare it against the source raster, then against the reviewed SVG.
- Fix conversion errors.
- Document unavoidable approximations.
- If the validation loop bails out, follow the Bailout Reporting format in `procedures/render-compare-iterate.md` and surface the partial result to the user.

Apply `criteria/visual-fidelity.md` for the final pass/fail standard and approval checklist.

## Stop Conditions

Stop only when one of these holds:

- **Success** — every applicable file in `criteria/` passes, requested outputs render correctly, platform outputs are consistent with the reviewed SVG, and unavoidable approximations are documented.
- **Bailout** — a bailout condition fires (iteration cap, stalled progress, regression). On bailout, hand the partial result to the user with the violation list described in `procedures/render-compare-iterate.md` ("Bailout Reporting"). Do not declare the result "done".

For the iterate-loop mechanics and full bailout rules see `procedures/render-compare-iterate.md`. For the pass/fail standard and approval checklist see `criteria/visual-fidelity.md`.

## Skill-level Do Not

- Do not generate unrequested output formats.
- Do not invent project-specific design tokens, helpers, or resources.
- Do not eyeball pixel coordinates from a render or screenshot.

General iteration rules (source of truth, do-not-approve-from-data, do-not-hide-mismatches, do-not-optimize-early, raster handling) live in `criteria/visual-fidelity.md`.

## Deliverables

Provide the requested output files or code. When useful, also provide:

- reviewed SVG intermediate
- rendered comparison image
- zoom inspection panels
- notes on approximations or limitations
