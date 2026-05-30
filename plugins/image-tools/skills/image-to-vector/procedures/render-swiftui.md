# Render SwiftUI

## Purpose

Render generated SwiftUI vector code to a PNG so it can be compared against the source raster (and the reviewed SVG, if used as an intermediate).

Use this when SwiftUI output is requested and a Swift/macOS rendering environment is available. If rendering is not available, state that limitation and still inspect the code for geometry, scaling, fill, stroke, opacity, gradient, and fill-rule conversion issues.

Core rules (do not approve from code alone, do not hide mismatches with padding/scaling/clipping/background) live in `criteria/visual-fidelity.md`.

## Preferred Approach

Use a small temporary SwiftPM executable to render the generated SwiftUI component with `ImageRenderer`. This produces a PNG that can be fed into `procedures/render-compare-iterate.md`.

## Requirements for Renderable SwiftUI

The generated SwiftUI should be easy to instantiate in a render harness. Prefer one of:

```swift
IconView(size: 1024)
```

or:

```swift
IconView()
    .frame(width: 1024, height: 1024)
```

## Temporary SwiftPM Harness

Create a temporary SwiftPM executable target:

```sh
mkdir -p /tmp/swiftui_render/Sources
cd /tmp/swiftui_render

cat > Package.swift <<'EOF'
import PackageDescription

let package = Package(
    name: "SwiftUIRender",
    platforms: [.macOS(.v13)],
    targets: [
        .executableTarget(name: "SwiftUIRender", path: "Sources")
    ]
)
EOF
```

Copy the generated SwiftUI file into `Sources/`. Create `Sources/main.swift`:

```swift
import SwiftUI
import AppKit

@MainActor
func main() throws {
    guard CommandLine.arguments.count >= 3 else {
        fatalError("usage: SwiftUIRender <output.png> <size>")
    }

    let outPath = CommandLine.arguments[1]
    let size = CGFloat(Double(CommandLine.arguments[2]) ?? 1024)

    let view = <StructName>(size: size)
        .frame(width: size, height: size)

    let renderer = ImageRenderer(content: view)
    renderer.scale = 1

    guard let cgImage = renderer.cgImage else {
        fatalError("render failed")
    }

    let bitmap = NSBitmapImageRep(cgImage: cgImage)
    guard let data = bitmap.representation(using: .png, properties: [:]) else {
        fatalError("png encode failed")
    }

    try data.write(to: URL(fileURLWithPath: outPath))
}

try main()
```

Run:

```sh
swift run SwiftUIRender /tmp/rendered-swiftui.png 1024
```

Replace `<StructName>` with the generated SwiftUI component name.

## If the Component Does Not Use `size`

Render with a frame:

```swift
let view = <StructName>()
    .frame(width: size, height: size)
```

Use the generated component's actual initializer. Do not rewrite the component just to fit the harness unless the change preserves output fidelity.

## Render Sizes

Render at the source raster size when possible. Also render at small UI sizes (e.g. 32, 64, 128) — small renders often reveal alignment, stroke, and scaling problems that are not obvious at large size.

## After Rendering

Feed the rendered PNG into `procedures/render-compare-iterate.md` (which handles diff, criteria, and the convergence rule) and `procedures/zoom-inspection.md`.

Compare against:

1. the source raster
2. the reviewed SVG, if SVG was used as an intermediate

## Fallbacks

If the SwiftPM renderer is not practical:

- use Xcode Preview screenshots
- use an app/simulator screenshot
- use a project-specific snapshot test
- inspect code manually and document that raster rendering was not performed
