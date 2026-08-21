# SwiftUI Output Rules

## Role

Use SwiftUI output when the requested target is an Apple app using SwiftUI. When practical, derive SwiftUI from the reviewed SVG or shared vector geometry.

## Supported Forms

Use the form that best fits the request:

- reusable `View`
- `Shape`
- `Path` drawing function

Prefer reusable `View` or `Shape` for app use.

## Requirements

- Preserve the reviewed vector geometry and source aspect ratio.
- Use coordinates from the SVG `viewBox` or explicitly normalize them.
- Use `Path { path in ... }` for custom geometry.
- Convert SVG path commands accurately:
  - `M` -> `move(to:)`
  - `L` -> `addLine(to:)`
  - `C` -> `addCurve(to:control1:control2:)`
  - `Q` -> convert to cubic Bezier when needed
  - `Z` -> `closeSubpath()`
- Preserve fills, strokes, opacity, line caps, line joins, and miter behavior where visually relevant.
- Use `FillStyle(eoFill: true)` when needed for holes/counters. Put every
  subpath in **one** `Path`: separate shapes each fill solid and paint over
  the counter instead of cutting through it. Even-odd also means the hole
  works whatever winding direction the trace produced, which is worth
  having — vtracer's winding is not something to rely on.
- Note the interaction with tinting. Rendering a `Shape` directly as a view
  makes it take the ambient `foregroundStyle`, which is usually what you
  want, but gives no way to choose a fill rule. A shape with counters needs
  `.fill(.foreground, style: FillStyle(eoFill: true))` to get both — that
  spelling requires iOS 17 / macOS 14, so on an older target either pass an
  explicit colour or orient the hole's winding to suit a nonzero fill.
- Use SwiftUI gradients only when the source/reviewed vector requires gradients.
- Keep generated Swift code reusable and paste-ready.

## Project Conventions

When generating SwiftUI for an existing project, use existing design tokens when they clearly match the source colors. Use literal SwiftUI colors only when no token matches.

Do not invent helpers such as `Color(hex:)` unless the project already supports them. Follow project guidance such as `CLAUDE.md` when available.

## Sizing

Match the source image's visual bounds. If the raster content fills the image, the SwiftUI rendering should fill its requested frame.

## Component Structure

For standalone SwiftUI output, prefer a reusable `View` or `Shape`. Draw layers back-to-front, preserve frame calibration, and expose only useful configuration such as size or color overrides.

Include a multi-size `#Preview` when practical; small-size previews often reveal path, alignment, and stroke issues.
