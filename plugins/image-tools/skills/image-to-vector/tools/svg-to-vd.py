#!/usr/bin/env python3
"""svg-to-vd.py — convert a reviewed SVG into Android VectorDrawable XML.

This is the mechanical half of `outputs/android-vectordrawable.md`: path data
is copied verbatim (VectorDrawable accepts full SVG path syntax), so every
coordinate stays traceable to the reviewed SVG. Anything VectorDrawable
cannot express is an ERROR rather than a silent approximation; fix the SVG
and re-run.

VectorDrawable limits, and what this tool does about each:

  * Only path data. <rect>, <circle>, <ellipse>, <line>, <polyline> and
    <polygon> become pathData; circles and ellipses as FOUR quarter arcs,
    never two half arcs (see "Android renderer pitfalls").
  * Groups take only translate, scale, rotation and pivot. SVG transforms
    become nested <group>s; matrix() is decomposed when it has no skew.
    skewX/skewY, or a skewed matrix() -> error (bake the transform into the
    path data first).
  * No masks, only clip paths. clip-path="url(#id)" becomes a <clip-path>
    at the top of a wrapping <group> (it clips the group's later content,
    as SVG's does). objectBoundingBox clip units -> error.
  * Groups have no alpha. A group's opacity is multiplied into each child's
    fillAlpha/strokeAlpha, which is exact only when the children do not
    overlap; reported as a warning.
  * Gradients: linear and radial, gradientUnits="userSpaceOnUse", no
    gradientTransform; written as <aapt:attr> blocks. Anything else -> error.
  * Not supported at all (error): <use>, <image>, <text>, <mask>, <pattern>,
    <style> sheets / class selectors (inline them first), filter=, mask=.
    stroke-dasharray is dropped with a warning.

Defaults differ, and are written out explicitly where it matters: SVG's
unspecified fill is black and VectorDrawable's is none; SVG's unspecified
stroke-width is 1 and VectorDrawable's is 0.

Any arc segment spanning 180 deg or more in the copied path data is
reported (the check is shared with vd-to-svg.py).

Usage:
  python3 svg-to-vd.py REVIEWED.svg OUT.xml [--dp 24] [--current-color '#FFFFFF']

--dp sets the longer side's android:width/height in dp (default: the
viewBox size). Validate the result with Android's renderer, per
`procedures/render-compare-iterate.md`.

Requires: Python >= 3.10, standard library only.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ANDROID = "http://schemas.android.com/apk/res/android"
AAPT_NS = "http://schemas.android.com/aapt"
A = "{" + ANDROID + "}"
ET.register_namespace("android", ANDROID)
ET.register_namespace("aapt", AAPT_NS)

_spec = importlib.util.spec_from_file_location("vd_to_svg", Path(__file__).with_name("vd-to-svg.py"))
_vd_to_svg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_vd_to_svg)
wide_arcs = _vd_to_svg.wide_arcs

INHERITED = ("fill", "fill-opacity", "fill-rule", "stroke", "stroke-width", "stroke-opacity",
             "stroke-linecap", "stroke-linejoin", "stroke-miterlimit", "stroke-dasharray",
             "clip-rule", "color")
SHAPES = ("path", "rect", "circle", "ellipse", "line", "polyline", "polygon")
SKIPPED = ("defs", "title", "desc", "metadata", "clipPath", "linearGradient",
           "radialGradient", "symbol")
UNSUPPORTED = ("use", "image", "text", "mask", "pattern", "style", "foreignObject", "switch", "svg")
NAMED = {"black": "#000000", "white": "#ffffff", "red": "#ff0000", "green": "#008000",
         "blue": "#0000ff", "gray": "#808080", "grey": "#808080"}


class ConversionError(Exception):
    pass


def warn(msg: str) -> None:
    print(f"warning: {msg}", file=sys.stderr)


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def fmt(v: float) -> str:
    return f"{v:.6g}"


def length(s: str | None, default: float = 0.0) -> float:
    if s is None or s == "":
        return default
    s = s.strip()
    if s.endswith("%"):
        raise ConversionError(f"percentage length {s!r} not supported; use user units")
    return float(re.sub(r"(px|pt|dp)$", "", s))


def numbers(s: str) -> list[float]:
    return [float(v) for v in re.findall(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", s)]


def own_style(el: ET.Element) -> dict[str, str]:
    props = {k: v for k, v in el.attrib.items() if "}" not in k}
    for decl in el.get("style", "").split(";"):
        if ":" in decl:
            k, v = decl.split(":", 1)
            props[k.strip()] = v.strip()
    return props


# ------------------------------------------------------------------ colours

def color(value: str, current: str | None) -> tuple[str, float] | None:
    """(#RRGGBB, alpha) for an SVG colour; None for 'none'."""
    v = value.strip().lower()
    if v == "none":
        return None
    if v == "transparent":
        return "#000000", 0.0
    if v == "currentcolor":
        if current is None:
            raise ConversionError("currentColor used; pass --current-color '#RRGGBB'")
        v = current.lower()
    v = NAMED.get(v, v)
    if v.startswith("#"):
        h = v[1:]
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        if len(h) == 6:
            return "#" + h.upper(), 1.0
        if len(h) == 8:
            return "#" + h[:6].upper(), int(h[6:], 16) / 255
    m = re.fullmatch(r"rgba?\((.*)\)", v)
    if m:
        parts = [p.strip() for p in re.split(r"[,\s/]+", m.group(1)) if p.strip()]
        rgb = [round(float(p[:-1]) * 2.55) if p.endswith("%") else round(float(p))
               for p in parts[:3]]
        alpha = 1.0
        if len(parts) > 3:
            alpha = float(parts[3][:-1]) / 100 if parts[3].endswith("%") else float(parts[3])
        return "#" + "".join(f"{c:02X}" for c in rgb), alpha
    raise ConversionError(f"unsupported colour {value!r}")


def argb(rgb: str, alpha: float) -> str:
    return rgb if alpha >= 1 else f"#{round(alpha * 255):02X}{rgb[1:]}"


# --------------------------------------------------------------- transforms

def transform_ops(s: str) -> list[tuple[str, list[float]]]:
    """Split an SVG transform list into (op, args), with matrix() decomposed."""
    ops = []
    for name, args in re.findall(r"(\w+)\s*\(([^)]*)\)", s):
        v = numbers(args)
        if name == "translate":
            ops.append(("translate", [v[0], v[1] if len(v) > 1 else 0.0]))
        elif name == "scale":
            ops.append(("scale", [v[0], v[1] if len(v) > 1 else v[0]]))
        elif name == "rotate":
            ops.append(("rotate", [v[0], *(v[1:3] if len(v) >= 3 else [0.0, 0.0])]))
        elif name == "matrix":
            a, b, c, d, e, f = v
            sx = math.hypot(a, b)
            if sx == 0 or abs(a * c + b * d) > 1e-6 * max(1.0, sx * math.hypot(c, d)):
                raise ConversionError(f"skewed matrix({args}) cannot be a <group>; bake it into the path")
            sy = (a * d - b * c) / sx
            if e or f:
                ops.append(("translate", [e, f]))
            if b:
                ops.append(("rotate", [math.degrees(math.atan2(b, a)), 0.0, 0.0]))
            if not (math.isclose(sx, 1) and math.isclose(sy, 1)):
                ops.append(("scale", [sx, sy]))
        else:
            raise ConversionError(f"{name}() cannot be a <group>; bake it into the path")
    return ops


def open_groups(parent: ET.Element, ops: list[tuple[str, list[float]]]) -> ET.Element:
    """Nest <group>s for the ops, packing translate -> rotate -> scale runs.

    One Android group computes translate(t+p) rotate(r) scale(s) translate(-p),
    so a run of translate, unpivoted rotate, scale in that order fits in one.
    """
    slots = {"translate": 0, "rotate": 1, "scale": 2}
    group, last = None, 3
    for op, v in ops:
        pivoted = op == "rotate" and (v[1] or v[2])
        if group is None or slots[op] <= last or pivoted:
            group = parent = ET.SubElement(parent, "group")
            last = -1
        if op == "translate":
            group.set(A + "translateX", fmt(v[0]))
            group.set(A + "translateY", fmt(v[1]))
        elif op == "rotate":
            group.set(A + "rotation", fmt(v[0]))
            if pivoted:
                group.set(A + "pivotX", fmt(v[1]))
                group.set(A + "pivotY", fmt(v[2]))
        else:
            group.set(A + "scaleX", fmt(v[0]))
            group.set(A + "scaleY", fmt(v[1]))
        last = 3 if pivoted else slots[op]
    return parent


# ------------------------------------------------------------------- shapes

def ellipse_d(cx: float, cy: float, rx: float, ry: float) -> str:
    # Four quarter arcs: Android mis-draws a full ellipse written as two half arcs.
    r = f"A{fmt(rx)},{fmt(ry)} 0 0 1"
    return (f"M{fmt(cx + rx)},{fmt(cy)} {r} {fmt(cx)},{fmt(cy + ry)} {r} {fmt(cx - rx)},{fmt(cy)} "
            f"{r} {fmt(cx)},{fmt(cy - ry)} {r} {fmt(cx + rx)},{fmt(cy)} Z")


def shape_d(el: ET.Element, tag: str) -> str:
    g = el.get
    if tag == "path":
        return g("d", "")
    if tag == "circle":
        r = length(g("r"))
        return ellipse_d(length(g("cx")), length(g("cy")), r, r)
    if tag == "ellipse":
        return ellipse_d(length(g("cx")), length(g("cy")), length(g("rx")), length(g("ry")))
    if tag == "line":
        return f"M{fmt(length(g('x1')))},{fmt(length(g('y1')))} L{fmt(length(g('x2')))},{fmt(length(g('y2')))}"
    if tag in ("polyline", "polygon"):
        v = numbers(g("points", ""))
        pts = [f"{fmt(v[i])},{fmt(v[i + 1])}" for i in range(0, len(v) - 1, 2)]
        return "M" + " L".join(pts) + (" Z" if tag == "polygon" else "")
    x, y, w, h = (length(g(k)) for k in ("x", "y", "width", "height"))
    rx, ry = g("rx"), g("ry")
    rx = length(rx if rx not in (None, "auto") else ry)
    ry = length(ry if ry not in (None, "auto") else g("rx"))
    rx, ry = min(rx, w / 2), min(ry, h / 2)
    if not rx or not ry:
        return f"M{fmt(x)},{fmt(y)} H{fmt(x + w)} V{fmt(y + h)} H{fmt(x)} Z"
    a = f"A{fmt(rx)},{fmt(ry)} 0 0 1"
    return (f"M{fmt(x + rx)},{fmt(y)} H{fmt(x + w - rx)} {a} {fmt(x + w)},{fmt(y + ry)} "
            f"V{fmt(y + h - ry)} {a} {fmt(x + w - rx)},{fmt(y + h)} H{fmt(x + rx)} "
            f"{a} {fmt(x)},{fmt(y + h - ry)} V{fmt(y + ry)} {a} {fmt(x + rx)},{fmt(y)} Z")


# ---------------------------------------------------------------- converter

class Converter:
    def __init__(self, root: ET.Element, current: str | None):
        self.current = current
        self.ids = {el.get("id"): el for el in root.iter() if el.get("id")}

    def ref(self, value: str, kind: tuple[str, ...]) -> ET.Element:
        m = re.fullmatch(r"\s*url\(\s*['\"]?#([^)'\"]+)['\"]?\s*\)\s*", value)
        el = self.ids.get(m.group(1)) if m else None
        if el is None or local(el.tag) not in kind:
            raise ConversionError(f"cannot resolve {value!r} to a {'/'.join(kind)}")
        return el

    def grad_attr(self, el: ET.Element, name: str) -> str | None:
        seen = set()
        while el is not None and id(el) not in seen:
            seen.add(id(el))
            if el.get(name) is not None:
                return el.get(name)
            href = el.get("href") or el.get("{http://www.w3.org/1999/xlink}href")
            el = self.ids.get(href[1:]) if href else None
        return None

    def gradient(self, value: str, attr: str, parent: ET.Element) -> None:
        g = self.ref(value, ("linearGradient", "radialGradient"))
        if self.grad_attr(g, "gradientUnits") != "userSpaceOnUse":
            raise ConversionError(f"gradient {value}: needs gradientUnits=\"userSpaceOnUse\"")
        if self.grad_attr(g, "gradientTransform"):
            raise ConversionError(f"gradient {value}: gradientTransform not supported; bake it into the coordinates")
        wrapper = ET.SubElement(parent, "{" + AAPT_NS + "}attr", name="android:" + attr)
        out = ET.SubElement(wrapper, "gradient")
        get = lambda k, d="0": self.grad_attr(g, k) or d  # noqa: E731
        if local(g.tag) == "linearGradient":
            out.set(A + "type", "linear")
            for svg_k, vd_k, d in (("x1", "startX", "0"), ("y1", "startY", "0"),
                                   ("x2", "endX", None), ("y2", "endY", "0")):
                if d is None and get(svg_k, "") == "":
                    raise ConversionError(f"gradient {value}: x2 must be explicit in user space")
                out.set(A + vd_k, fmt(length(get(svg_k, d))))
        else:
            out.set(A + "type", "radial")
            out.set(A + "centerX", fmt(length(get("cx"))))
            out.set(A + "centerY", fmt(length(get("cy"))))
            out.set(A + "gradientRadius", fmt(length(get("r"))))
            if get("fx", get("cx")) != get("cx") or get("fy", get("cy")) != get("cy"):
                warn(f"gradient {value}: focal point ignored (VectorDrawable has none)")
        spread = get("spreadMethod", "pad")
        if spread != "pad":
            out.set(A + "tileMode", {"repeat": "repeat", "reflect": "mirror"}[spread])
        holder, seen = g, set()
        while not holder.findall("{*}stop") and id(holder) not in seen:
            seen.add(id(holder))
            href = holder.get("href") or holder.get("{http://www.w3.org/1999/xlink}href")
            if not href or href[1:] not in self.ids:
                break
            holder = self.ids[href[1:]]
        for stop in holder.findall("{*}stop"):
            st = own_style(stop)
            off = st.get("offset", "0")
            off = float(off[:-1]) / 100 if off.endswith("%") else float(off)
            rgb, alpha = color(st.get("stop-color", "black"), self.current) or ("#000000", 0.0)
            alpha *= float(st.get("stop-opacity", "1"))
            ET.SubElement(out, "item", {A + "offset": fmt(off), A + "color": argb(rgb, alpha)})

    def clip(self, value: str, parent: ET.Element) -> None:
        cp = self.ref(value, ("clipPath",))
        if cp.get("clipPathUnits", "userSpaceOnUse") != "userSpaceOnUse":
            raise ConversionError(f"clip {value}: only clipPathUnits=\"userSpaceOnUse\" is supported")
        if cp.get("transform") or cp.get("clip-path"):
            raise ConversionError(f"clip {value}: transform/nested clip-path on <clipPath> not supported")
        parts = []
        for child in cp:
            tag = local(child.tag)
            if tag not in SHAPES:
                raise ConversionError(f"clip {value}: <{tag}> inside <clipPath> not supported")
            if child.get("transform"):
                raise ConversionError(f"clip {value}: transform on a clip shape; bake it into the path")
            if own_style(child).get("clip-rule") == "evenodd":
                warn(f"clip {value}: clip-rule=evenodd treated as nonzero")
            parts.append(shape_d(child, tag))
        ET.SubElement(parent, "clip-path", {A + "pathData": " ".join(parts)})

    def wrap(self, el: ET.Element, parent: ET.Element, style: dict) -> ET.Element:
        """Open transform groups and a clip group for el; return where its content goes."""
        if el.get("transform"):
            parent = open_groups(parent, transform_ops(el.get("transform")))
        clip = style.get("clip-path")
        if clip and clip != "none":
            parent = ET.SubElement(parent, "group")
            self.clip(clip, parent)
        return parent

    def path(self, el: ET.Element, tag: str, parent: ET.Element, style: dict, opacity: float) -> None:
        d = shape_d(el, tag)
        label = el.get("id") or f"<{tag}>"
        for sweep in wide_arcs(d):
            warn(f"{label}: arc spanning {sweep:.0f} deg; split it into arcs of 90 deg or less")
        p = ET.SubElement(parent, "path")
        if el.get("id"):
            p.set(A + "name", el.get("id"))
        p.set(A + "pathData", d)
        fill = style.get("fill", "black")
        if fill.startswith("url("):
            self.gradient(fill, "fillColor", p)
            alpha = opacity * float(style.get("fill-opacity", "1"))
            if alpha < 1:
                p.set(A + "fillAlpha", fmt(alpha))
        elif (c := color(fill, self.current)) is not None:
            p.set(A + "fillColor", c[0])
            alpha = c[1] * opacity * float(style.get("fill-opacity", "1"))
            if alpha < 1:
                p.set(A + "fillAlpha", fmt(alpha))
        if fill != "none" and style.get("fill-rule") == "evenodd":
            p.set(A + "fillType", "evenOdd")
        stroke = style.get("stroke", "none")
        if stroke == "none":
            return
        if stroke.startswith("url("):
            self.gradient(stroke, "strokeColor", p)
            alpha = opacity
        else:
            c = color(stroke, self.current)
            if c is None:
                return
            p.set(A + "strokeColor", c[0])
            alpha = c[1] * opacity
        alpha *= float(style.get("stroke-opacity", "1"))
        if alpha < 1:
            p.set(A + "strokeAlpha", fmt(alpha))
        p.set(A + "strokeWidth", fmt(length(style.get("stroke-width"), 1.0)))
        for svg_k, vd_k, default in (("stroke-linecap", "strokeLineCap", "butt"),
                                     ("stroke-linejoin", "strokeLineJoin", "miter")):
            v = style.get(svg_k, default)
            if v not in ("butt", "round", "square", "miter", "bevel"):
                raise ConversionError(f"{label}: {svg_k}={v} not supported")
            if v != default:
                p.set(A + vd_k, v)
        if style.get("stroke-miterlimit", "4") != "4":
            p.set(A + "strokeMiterLimit", fmt(float(style["stroke-miterlimit"])))
        if style.get("stroke-dasharray", "none") != "none":
            warn(f"{label}: stroke-dasharray dropped (VectorDrawable has no dashes)")
        if opacity < 1 and fill != "none":
            warn(f"{label}: opacity on a filled and stroked shape is approximated per paint")

    def walk(self, el: ET.Element, parent: ET.Element, inherited: dict, opacity: float) -> None:
        for child in el:
            if not isinstance(child.tag, str):
                continue
            tag = local(child.tag)
            if tag in SKIPPED:
                continue
            if tag in UNSUPPORTED:
                raise ConversionError(f"<{tag}> is not supported; flatten it to paths first")
            st = own_style(child)
            if st.get("display") == "none" or st.get("visibility") == "hidden":
                continue
            for attr in ("mask", "filter"):
                if st.get(attr, "none") != "none":
                    raise ConversionError(f"{attr}= on <{tag}> is not supported by VectorDrawable")
            if child.get("class"):
                raise ConversionError("class= styling found; inline the styles first (e.g. svgo inlineStyles)")
            style = {**inherited, **{k: v for k, v in st.items() if k in INHERITED}}
            style["clip-path"] = st.get("clip-path", "none")
            alpha = opacity * float(st.get("opacity", "1"))
            target = self.wrap(child, parent, style)
            if tag in SHAPES:
                self.path(child, tag, target, style, alpha)
            elif tag in ("g", "a"):
                if alpha < 1 and sum(local(c.tag) in SHAPES + ("g",) for c in child) > 1:
                    warn(f"opacity on <{tag} id={child.get('id')}> pushed into each child; "
                         "overlapping children will blend differently")
                self.walk(child, target, style, alpha)
            else:
                warn(f"<{tag}> ignored")

    def convert(self, root: ET.Element, dp: float | None) -> ET.Element:
        if local(root.tag) != "svg":
            raise ConversionError(f"root element is <{local(root.tag)}>, expected <svg>")
        if root.get("viewBox"):
            vx, vy, vw, vh = numbers(root.get("viewBox"))
        else:
            vx = vy = 0.0
            vw, vh = length(root.get("width")), length(root.get("height"))
        if dp is None:
            w, h = vw, vh
        else:
            scale = dp / max(vw, vh)
            w, h = vw * scale, vh * scale
        vec = ET.Element("vector", {A + "width": f"{fmt(w)}dp", A + "height": f"{fmt(h)}dp",
                                    A + "viewportWidth": fmt(vw), A + "viewportHeight": fmt(vh)})
        top = vec
        if vx or vy:
            top = ET.SubElement(vec, "group", {A + "translateX": fmt(-vx), A + "translateY": fmt(-vy)})
        st = own_style(root)
        style = {k: v for k, v in st.items() if k in INHERITED}
        self.walk(root, top, style, float(st.get("opacity", "1")))
        return vec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--dp", type=float, help="android:width/height of the longer side, in dp")
    ap.add_argument("--current-color", help="value for currentColor, e.g. '#FFFFFF'")
    args = ap.parse_args()
    root = ET.parse(args.input).getroot()
    try:
        vec = Converter(root, args.current_color).convert(root, args.dp)
    except ConversionError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    ET.indent(vec)
    Path(args.output).write_text(ET.tostring(vec, encoding="unicode") + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
