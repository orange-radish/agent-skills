# Port From SwiftUI

## Purpose

Read SwiftUI drawing code as the **source** for another format, usually Android VectorDrawable or SVG. This is part of the vector-source route in `SKILL.md`. `outputs/swiftui.md` covers the opposite direction.

The numbers come from the SwiftUI code, so the coordinate-traceability rule is satisfied as long as you take them from SwiftUI rather than re-deriving them by eye.

## Preferred: Dump SwiftUI's Own Path

Don't reimplement SwiftUI's geometry by hand. Ask SwiftUI for the resolved path and port its elements exactly. That avoids every pitfall listed below, because SwiftUI has already resolved continuous corners, tangent arcs and flipped `clockwise:` values into plain lines and curves.

Reuse the SwiftPM harness from `procedures/render-swiftui.md` (copy the source file into `Sources/`), and add a dump entry point:

```swift
import SwiftUI

func dump(_ path: Path) {
    path.forEach { element in
        switch element {
        case .move(let p):               print("M\(p.x),\(p.y)")
        case .line(let p):               print("L\(p.x),\(p.y)")
        case .quadCurve(let p, let c):   print("Q\(c.x),\(c.y) \(p.x),\(p.y)")
        case .curve(let p, let c1, let c2):
            print("C\(c1.x),\(c1.y) \(c2.x),\(c2.y) \(p.x),\(p.y)")
        case .closeSubpath:              print("Z")
        }
    }
}

// The rect is the frame the source view draws the shape in, in points.
let rect = CGRect(x: 0, y: 0, width: 24, height: 24)
dump(RoundedRectangle(cornerRadius: 6).path(in: rect))
dump(MyMarkShape().path(in: rect))
```

- The output is already SVG/VectorDrawable path syntax, in SwiftUI's y-down coordinates, which match the viewport. No flip is needed.
- Use the frame the source view really uses: its `.frame`, padding, and centering. Then add any offset or scale the view applies to the shape on top, so the dumped path lands where the shape is drawn in the viewport.
- For `strokeBorder(lineWidth:)`, dump `shape.inset(by: lineWidth / 2).path(in: rect)` and stroke that path. See below.
- Round to a fixed precision, such as 3 decimals, and keep the dump output with your working notes as the trace for the numbers.

## Pitfalls When Porting By Hand

Port by hand only when you can't run the harness, for example when the code isn't macOS-compilable. Each of these cost a real iteration on a previous port:

- **`RoundedRectangle` corners are continuous by default.** In current SDKs, `RoundedRectangle(cornerRadius:)` defaults to `style: .continuous`, a squircle-like curve. Its corners aren't circular arcs, so approximating them with `A` arcs leaves a visible error; one such frame was 333 px off at 512 px. Dump the path, or check that the source explicitly says `style: .circular`.
- **`strokeBorder` strokes inside the shape.** The stroke sits entirely inside the frame, so its centerline is half a stroke width in from the shape's edge. VectorDrawable and SVG strokes are centered on the path, so inset the path by `lineWidth / 2`.
- **`addArc(tangent1End:tangent2End:radius:)` is a line plus an arc.** It adds a straight line from the current point to the first tangent point, then the arc. It is not a single arc.
- **`clockwise:` is in flipped coordinates.** `addArc(center:radius:startAngle:endAngle:clockwise:)` measures direction in SwiftUI's y-down space, so `clockwise: true` draws **counter-clockwise** on screen. Set the SVG sweep flag from what is drawn on screen, not from the parameter name.
- **Normalized tables.** If the source keeps points in a 0–1 box and scales them by aspect ratio and centers them in the frame at draw time, apply the same scale and centering when converting to the viewport. Don't just multiply by the viewport size.
- **Stroke defaults differ.** SwiftUI's `StrokeStyle` defaults to butt caps, miter joins and **miter limit 10**. VectorDrawable and SVG default to miter limit 4. Set `android:strokeMiterLimit="10"` explicitly when sharp joins are involved.
- **Arcs of 180° or more.** If the SwiftUI code draws a full circle with `addArc` or `addEllipse`, write the port as four quarter arcs. See "Android renderer pitfalls" in `outputs/android-vectordrawable.md`.

## Fill Rules

- `.fill(style: FillStyle(eoFill: true))` becomes `android:fillType="evenOdd"` or `fill-rule="evenodd"`.
- A plain `.fill()` is nonzero, the default in all three formats.

## Reference Render

Render the **source** SwiftUI view with `procedures/render-swiftui.md` at the comparison size. That PNG is the reference for `procedures/render-compare-iterate.md`. Render the port with its target's own renderer; for Android, that's the Robolectric capture.
