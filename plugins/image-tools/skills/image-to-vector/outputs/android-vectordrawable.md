# Android VectorDrawable Output Rules

## Role

Use Android VectorDrawable XML when the requested target is an Android app vector asset. Derive it from the reviewed SVG, or port it straight from the vector source when you're on the vector-source route (`SKILL.md`).

From a reviewed SVG, convert mechanically:

```sh
python3 tools/svg-to-vd.py reviewed.svg res/drawable/<name>.xml --dp 24
```

The converter copies path data verbatim, turns shapes into path data, turns transforms into `<group>` attributes and turns `clip-path` into a `<clip-path>` inside a group. It refuses anything VectorDrawable cannot express, such as skew, masks, `<use>`, `<text>` and object-bounding-box gradients, instead of approximating it. Fix the SVG and re-run.

VectorDrawable is the preferred Android asset format for static vector images because it scales across densities from a single XML resource.

## Requirements

- Output valid Android VectorDrawable XML.
- Use `<vector>` as the root element.
- Set `android:width` and `android:height` for the default rendered size.
- Set `android:viewportWidth` and `android:viewportHeight` to match the reviewed vector coordinate system.
- Preserve the source aspect ratio.
- Use `<path android:pathData="...">` for vector geometry.
- Draw paths in correct back-to-front order.
- Preserve fills, strokes, opacity, stroke width, line caps, line joins, and miter behavior where visually relevant.
- Use `android:fillType` when needed for holes, counters, and cutouts.
- Use Android VectorDrawable gradient features only when the source requires gradients; document any approximation caused by VectorDrawable limitations.
- Remove unsupported SVG features or convert them into supported VectorDrawable features.
- Keep XML clean, minimal, and resource-ready.

## Fill Rules

For holes, counters, and cutouts, use the appropriate fill behavior:

`android:fillType="evenOdd"`

or:

`android:fillType="nonZero"`

Match the reviewed vector geometry. Do not change the source shape just to simplify the path.

## Android Renderer Pitfalls

These are cases where an SVG render (including the `tools/vd-to-svg.py` stand-in) looks right and Android's renderer does not, or where SVG features don't carry over. Check them by hand whenever you can't capture with Android's renderer (`procedures/render-compare-iterate.md`).

- **Arcs of 180° or more.** Write a circle or ellipse as **four quarter arcs**, never two half arcs. A ring written as two 180° arcs was observed ~115 px off at 512 px under Android's renderer while every SVG renderer drew it correctly. This was observed behavior and wasn't traced to the parser, so keep every arc at 90° or less. Both converters warn about wider arcs, and `svg-to-vd.py` already emits circles as quarter arcs.
- **Only path data.** There is no `<circle>`, `<rect>` or `<ellipse>`; shapes become `pathData`.
- **Groups only translate, scale, rotate (with pivot).** There is no matrix and no skew. Android composes a group as `translate(t + pivot) · rotate · scale · translate(−pivot)`. Bake a skew into the path data.
- **Clip paths, not masks.** A `<clip-path>` clips the content after it in the same `<group>`. Several clip paths in one group intersect.
- **Groups have no alpha.** Group opacity has to be multiplied into each path's `fillAlpha` and `strokeAlpha`. That is exact only when the children don't overlap.
- **Default differences.** An unspecified SVG fill is black, but VectorDrawable's is none. An unspecified SVG stroke width is 1, but VectorDrawable's is 0. The miter limit defaults to 4 in both, but to 10 in SwiftUI and Core Graphics.
- **Robolectric graphics mode.** Any test that inflates or renders drawables needs `@GraphicsMode(GraphicsMode.Mode.NATIVE)`. The default mode accepts malformed path data silently.

## Tinting

Decide whether the drawable is tinted at the call site before you choose its colors.

- **Single-color icons, tinted at the call site:** use one opaque fill and tint with `Icon(painter, contentDescription, tint = …)`. Compose's tint replaces the fill color and keeps only coverage, so a themed `@color/` or `?attr/` fill buys nothing. Match the fill color existing drawables in the project use; if there are none, white is the usual convention.
- **Multi-color art** (logos, illustrations): keep the literal or resource colors. Draw it untinted, either with `Image(painterResource(...))` or with `Icon(..., tint = Color.Unspecified)`. `Icon` tints with `LocalContentColor` by default and flattens the art to one color.
- Don't set `android:tint` on a drawable you author for call-site tinting. Keep the call site the only color source.

## Project Conventions

When generating XML for an existing Android project, use existing resources when they clearly match the source:

- `@color/...`
- `?attr/...`
- design-system color resources

Use literal colors such as `#RRGGBB` or `#AARRGGBB` only when no project resource clearly matches. This applies to colors that render as authored; for call-site-tinted icons see "Tinting".

Do not invent resources, themes, or helper conventions unless the project already uses them.

Check every authored or edited XML file before rendering, for example with `xmllint --noout res/drawable/<name>.xml`. A malformed file can still look plausible in a diff.

## Sizing

Match the source image's visual bounds. If the raster content fills the image, the VectorDrawable should fill its intended viewport.

## File Placement

For standalone Android assets, prefer:

`res/drawable/<name>.xml`

Use resource-safe lowercase names with underscores:

`orange_radish_icon.xml`

## Compose Usage

For Jetpack Compose apps, keep the VectorDrawable as a drawable resource and load it with `painterResource` when appropriate.

Example:

`Icon(painter = painterResource(R.drawable.orange_radish_icon), contentDescription = "Orange Radish")`

Do not convert to Compose `ImageVector` unless specifically requested.
