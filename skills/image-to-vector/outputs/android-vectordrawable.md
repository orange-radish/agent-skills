# Android VectorDrawable Output Rules

## Role

Use Android VectorDrawable XML when the requested target is an Android app vector asset. When practical, derive VectorDrawable from the reviewed SVG or shared vector geometry.

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

## Project Conventions

When generating XML for an existing Android project, use existing resources when they clearly match the source:

- `@color/...`
- `?attr/...`
- design-system color resources

Use literal colors such as `#RRGGBB` or `#AARRGGBB` only when no project resource clearly matches.

Do not invent resources, themes, or helper conventions unless the project already uses them.

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
