# SVG Output Rules

## Role

Use SVG as the canonical reviewed vector format when practical, especially when generating multiple platform outputs.

## Requirements

- Output valid standalone SVG.
- Use a correct `viewBox`.
- Preserve the source aspect ratio.
- Do not embed raster images.
- Prefer clean, editable paths over noisy auto-traced paths.
- Use appropriate `fill-rule` behavior for holes, counters, and cutouts.
- Preserve fills, strokes, opacity, joins, caps, and miter behavior where visually relevant.
- Preserve gradients with `<linearGradient>` or `<radialGradient>` when the source requires them.
- Remove unnecessary metadata, hidden layers, and tracing artifacts.
- Optimize only after visual validation.
