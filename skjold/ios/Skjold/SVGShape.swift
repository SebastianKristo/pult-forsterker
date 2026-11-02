import SwiftUI

/// Parses SVG path data (`d` attribute) so the icons from the design file can be drawn 1:1.
nonisolated enum SVGPathParser {
    static func parse(_ d: String) -> Path {
        var s = Scanner(Array(d.utf8))
        var path = Path()
        var cur = CGPoint.zero, start = CGPoint.zero
        var lastCtrl: CGPoint? = nil      // for S/s
        var lastQuad: CGPoint? = nil      // for T/t
        var cmd: UInt8 = 0

        while true {
            s.skipSeparators()
            guard let c = s.peek() else { break }
            if isCommand(c) { cmd = c; s.i += 1 } else if cmd == 0 { break }
            let rel = cmd >= 97 // lowercase
            let base = rel ? cur : .zero
            var ctrlSet = false, quadSet = false

            switch cmd {
            case UInt8(ascii: "M"), UInt8(ascii: "m"):
                guard let x = s.number(), let y = s.number() else { return path }
                cur = CGPoint(x: base.x + x, y: base.y + y)
                path.move(to: cur); start = cur
                cmd = rel ? UInt8(ascii: "l") : UInt8(ascii: "L")
            case UInt8(ascii: "L"), UInt8(ascii: "l"):
                guard let x = s.number(), let y = s.number() else { return path }
                cur = CGPoint(x: base.x + x, y: base.y + y); path.addLine(to: cur)
            case UInt8(ascii: "H"), UInt8(ascii: "h"):
                guard let x = s.number() else { return path }
                cur = CGPoint(x: (rel ? cur.x : 0) + x, y: cur.y); path.addLine(to: cur)
            case UInt8(ascii: "V"), UInt8(ascii: "v"):
                guard let y = s.number() else { return path }
                cur = CGPoint(x: cur.x, y: (rel ? cur.y : 0) + y); path.addLine(to: cur)
            case UInt8(ascii: "C"), UInt8(ascii: "c"):
                guard let x1 = s.number(), let y1 = s.number(), let x2 = s.number(), let y2 = s.number(),
                      let x = s.number(), let y = s.number() else { return path }
                let c2 = CGPoint(x: base.x + x2, y: base.y + y2)
                cur = CGPoint(x: base.x + x, y: base.y + y)
                path.addCurve(to: cur, control1: CGPoint(x: base.x + x1, y: base.y + y1), control2: c2)
                lastCtrl = c2; ctrlSet = true
            case UInt8(ascii: "S"), UInt8(ascii: "s"):
                guard let x2 = s.number(), let y2 = s.number(), let x = s.number(), let y = s.number() else { return path }
                let c1 = lastCtrl.map { CGPoint(x: 2 * cur.x - $0.x, y: 2 * cur.y - $0.y) } ?? cur
                let c2 = CGPoint(x: base.x + x2, y: base.y + y2)
                cur = CGPoint(x: base.x + x, y: base.y + y)
                path.addCurve(to: cur, control1: c1, control2: c2)
                lastCtrl = c2; ctrlSet = true
            case UInt8(ascii: "Q"), UInt8(ascii: "q"):
                guard let x1 = s.number(), let y1 = s.number(), let x = s.number(), let y = s.number() else { return path }
                let q = CGPoint(x: base.x + x1, y: base.y + y1)
                cur = CGPoint(x: base.x + x, y: base.y + y)
                path.addQuadCurve(to: cur, control: q); lastQuad = q; quadSet = true
            case UInt8(ascii: "T"), UInt8(ascii: "t"):
                guard let x = s.number(), let y = s.number() else { return path }
                let q = lastQuad.map { CGPoint(x: 2 * cur.x - $0.x, y: 2 * cur.y - $0.y) } ?? cur
                cur = CGPoint(x: base.x + x, y: base.y + y)
                path.addQuadCurve(to: cur, control: q); lastQuad = q; quadSet = true
            case UInt8(ascii: "A"), UInt8(ascii: "a"):
                guard let rx = s.number(), let ry = s.number(), let rot = s.number(),
                      let large = s.flag(), let sweep = s.flag(),
                      let x = s.number(), let y = s.number() else { return path }
                let end = CGPoint(x: base.x + x, y: base.y + y)
                addArc(&path, from: cur, to: end, rx: rx, ry: ry, angle: rot, large: large, sweep: sweep)
                cur = end
            case UInt8(ascii: "Z"), UInt8(ascii: "z"):
                path.closeSubpath(); cur = start
                cmd = 0
                s.skipSeparators()
                if let n = s.peek(), !isCommand(n) { return path }
                continue
            default:
                return path
            }
            if !ctrlSet { lastCtrl = nil }
            if !quadSet { lastQuad = nil }
        }
        return path
    }

    private static func isCommand(_ c: UInt8) -> Bool {
        switch c {
        case UInt8(ascii: "M"), UInt8(ascii: "m"), UInt8(ascii: "L"), UInt8(ascii: "l"), UInt8(ascii: "H"), UInt8(ascii: "h"),
             UInt8(ascii: "V"), UInt8(ascii: "v"), UInt8(ascii: "C"), UInt8(ascii: "c"), UInt8(ascii: "S"), UInt8(ascii: "s"),
             UInt8(ascii: "Q"), UInt8(ascii: "q"), UInt8(ascii: "T"), UInt8(ascii: "t"), UInt8(ascii: "A"), UInt8(ascii: "a"),
             UInt8(ascii: "Z"), UInt8(ascii: "z"): return true
        default: return false
        }
    }

    /// Endpoint arc → cubic Béziers (SVG implementation notes F.6).
    private static func addArc(_ path: inout Path, from p0: CGPoint, to p1: CGPoint, rx rx0: CGFloat, ry ry0: CGFloat,
                               angle: CGFloat, large: Bool, sweep: Bool) {
        var rx = abs(rx0), ry = abs(ry0)
        if rx == 0 || ry == 0 || p0 == p1 { path.addLine(to: p1); return }
        let phi = angle * .pi / 180, cosP = cos(phi), sinP = sin(phi)
        let dx = (p0.x - p1.x) / 2, dy = (p0.y - p1.y) / 2
        let x1 = cosP * dx + sinP * dy, y1 = -sinP * dx + cosP * dy
        let lambda = (x1 * x1) / (rx * rx) + (y1 * y1) / (ry * ry)
        if lambda > 1 { let k = sqrt(lambda); rx *= k; ry *= k }
        let num = rx * rx * ry * ry - rx * rx * y1 * y1 - ry * ry * x1 * x1
        let den = rx * rx * y1 * y1 + ry * ry * x1 * x1
        var coef = sqrt(max(0, num / den))
        if large == sweep { coef = -coef }
        let cx1 = coef * rx * y1 / ry, cy1 = -coef * ry * x1 / rx
        let cx = cosP * cx1 - sinP * cy1 + (p0.x + p1.x) / 2
        let cy = sinP * cx1 + cosP * cy1 + (p0.y + p1.y) / 2
        func ang(_ ux: CGFloat, _ uy: CGFloat, _ vx: CGFloat, _ vy: CGFloat) -> CGFloat {
            let a = atan2(ux * vy - uy * vx, ux * vx + uy * vy)
            return a
        }
        let t1 = ang(1, 0, (x1 - cx1) / rx, (y1 - cy1) / ry)
        var dt = ang((x1 - cx1) / rx, (y1 - cy1) / ry, (-x1 - cx1) / rx, (-y1 - cy1) / ry)
        if !sweep && dt > 0 { dt -= 2 * .pi } else if sweep && dt < 0 { dt += 2 * .pi }
        let segs = max(1, Int(ceil(abs(dt) / (.pi / 2))))
        let delta = dt / CGFloat(segs)
        let k = 4.0 / 3.0 * tan(delta / 4)
        var t = t1
        func pt(_ t: CGFloat) -> (CGPoint, CGPoint) {
            let ct = cos(t), st = sin(t)
            let p = CGPoint(x: cx + rx * ct * cosP - ry * st * sinP, y: cy + rx * ct * sinP + ry * st * cosP)
            let d = CGPoint(x: -rx * st * cosP - ry * ct * sinP, y: -rx * st * sinP + ry * ct * cosP)
            return (p, d)
        }
        for i in 0..<segs {
            let (pa, da) = pt(t)
            let (pb, db) = pt(t + delta)
            let end = i == segs - 1 ? p1 : pb
            path.addCurve(to: end,
                          control1: CGPoint(x: pa.x + k * da.x, y: pa.y + k * da.y),
                          control2: CGPoint(x: pb.x - k * db.x, y: pb.y - k * db.y))
            t += delta
        }
    }

    private struct Scanner {
        let b: [UInt8]
        var i = 0
        init(_ b: [UInt8]) { self.b = b }

        func peek() -> UInt8? { i < b.count ? b[i] : nil }

        mutating func skipSeparators() {
            while i < b.count, b[i] == 32 || b[i] == 44 || b[i] == 10 || b[i] == 13 || b[i] == 9 { i += 1 }
        }

        mutating func flag() -> Bool? {
            skipSeparators()
            guard i < b.count else { return nil }
            let c = b[i]
            guard c == 48 || c == 49 else { return nil }
            i += 1
            return c == 49
        }

        mutating func number() -> CGFloat? {
            skipSeparators()
            let st = i
            if i < b.count, b[i] == 43 || b[i] == 45 { i += 1 }
            var digits = false, dot = false
            while i < b.count {
                let c = b[i]
                if c >= 48 && c <= 57 { digits = true; i += 1 }
                else if c == 46 && !dot { dot = true; i += 1 }
                else { break }
            }
            if i < b.count, digits, b[i] == 101 || b[i] == 69 {
                var j = i + 1
                if j < b.count, b[j] == 43 || b[j] == 45 { j += 1 }
                if j < b.count, b[j] >= 48 && b[j] <= 57 {
                    i = j
                    while i < b.count, b[i] >= 48 && b[i] <= 57 { i += 1 }
                }
            }
            guard digits, let str = String(bytes: b[st..<i], encoding: .ascii), let v = Double(str) else { i = st; return nil }
            return CGFloat(v)
        }
    }
}

/// An SVG path in a square viewBox, scaled to fit the frame.
nonisolated struct SVGShape: Shape {
    let path: Path
    let viewBox: CGSize

    init(_ d: String, viewBox: CGFloat = 24) {
        self.path = SVGPathParser.parse(d)
        self.viewBox = CGSize(width: viewBox, height: viewBox)
    }

    init(_ d: String, viewBoxW: CGFloat, viewBoxH: CGFloat) {
        self.path = SVGPathParser.parse(d)
        self.viewBox = CGSize(width: viewBoxW, height: viewBoxH)
    }

    func path(in rect: CGRect) -> Path {
        let s = min(rect.width / viewBox.width, rect.height / viewBox.height)
        let ox = rect.minX + (rect.width - viewBox.width * s) / 2
        let oy = rect.minY + (rect.height - viewBox.height * s) / 2
        return path.applying(CGAffineTransform(a: s, b: 0, c: 0, d: s, tx: ox, ty: oy))
    }
}

/// Helpers that turn SVG primitives into path data.
nonisolated enum SVG {
    static func circle(_ cx: CGFloat, _ cy: CGFloat, _ r: CGFloat) -> String {
        "M\(cx - r) \(cy) a\(r) \(r) 0 1 0 \(2 * r) 0 a\(r) \(r) 0 1 0 \(-2 * r) 0Z"
    }

    static func rect(_ x: CGFloat, _ y: CGFloat, _ w: CGFloat, _ h: CGFloat, rx: CGFloat = 0) -> String {
        if rx <= 0 { return "M\(x) \(y)h\(w)v\(h)h\(-w)Z" }
        return "M\(x + rx) \(y)H\(x + w - rx)A\(rx) \(rx) 0 0 1 \(x + w) \(y + rx)V\(y + h - rx)A\(rx) \(rx) 0 0 1 \(x + w - rx) \(y + h)H\(x + rx)A\(rx) \(rx) 0 0 1 \(x) \(y + h - rx)V\(y + rx)A\(rx) \(rx) 0 0 1 \(x + rx) \(y)Z"
    }
}

/// Stroked/filled icon from the design (viewBox 0 0 24 24, round caps and joins).
struct SKIcon: View {
    let d: String
    var size: CGFloat = 24
    var stroke: CGFloat = 1.8
    var color: Color? = nil
    var fill = false
    var roundCap = true

    var body: some View {
        let shape = SVGShape(d)
        // nil colour = CSS currentColor (inherits the foreground style)
        let style: AnyShapeStyle = color.map { AnyShapeStyle($0) } ?? AnyShapeStyle(.foreground)
        Group {
            if fill {
                shape.fill(style)
            } else {
                shape.stroke(style, style: StrokeStyle(lineWidth: stroke * size / 24,
                                                       lineCap: roundCap ? .round : .butt,
                                                       lineJoin: .round))
            }
        }
        .frame(width: size, height: size)
    }
}

/// Paths used across the app (from the design file).
enum Icons {
    static let back = "M15 5l-7 7 7 7"
    static let chevronRight = "M9 5l7 7-7 7"
    static let chevronRight2 = "M9 6l6 6-6 6"
    static let chevronDown = "M6 9l6 6 6-6"
    static let chevronUp = "M6 15l6-6 6 6"
    static let plus = "M12 5v14M5 12h14"
    static let close = "M6 6l12 12M18 6L6 18"
    static let play = "M8 5v14l11-7z"
    static let playRound = "M8 5.2v13.6a1 1 0 0 0 1.52.85l10.6-6.8a1 1 0 0 0 0-1.7L9.52 4.35A1 1 0 0 0 8 5.2z"
    static let pause = SVG.rect(6, 4.5, 4, 15, rx: 1.2) + SVG.rect(14, 4.5, 4, 15, rx: 1.2)
    static let prev = SVG.rect(4, 5, 2.4, 14, rx: 1) + "M20 5.8v12.4a1 1 0 0 1-1.55.83L9.3 12.83a1 1 0 0 1 0-1.66l9.15-6.2A1 1 0 0 1 20 5.8z"
    static let next = SVG.rect(17.6, 5, 2.4, 14, rx: 1) + "M4 5.8v12.4a1 1 0 0 0 1.55.83l9.15-6.2a1 1 0 0 0 0-1.66l-9.15-6.2A1 1 0 0 0 4 5.8z"
    static let shuffle = "M16 3h5v5M4 20L21 3M21 16v5h-5M15 15l6 6M4 4l5 5"
    static let repeatIcon = "M17 2l4 4-4 4M3 11V9a3 3 0 0 1 3-3h15M7 22l-4-4 4-4M21 13v2a3 3 0 0 1-3 3H3"
    static let volume = "M4 9h3l5-4v14l-5-4H4zM16 9a4 4 0 0 1 0 6"
    static let queue = "M10 6h11M10 12h11M10 18h11M3 5l4 3-4 3z"
    static let speaker = SVG.rect(6, 3, 10, 18, rx: 2) + SVG.circle(11, 15, 2.5) + SVG.circle(11, 7.5, 1)
    static let more = SVG.circle(5, 12, 1.8) + SVG.circle(12, 12, 1.8) + SVG.circle(19, 12, 1.8)
    static let moreVertical = SVG.circle(12, 5, 1.9) + SVG.circle(12, 12, 1.9) + SVG.circle(12, 19, 1.9)
    static let favList = "M4 6h16M4 12h10M4 18h7M17 14l3 3-3 3"
    static let tabHome = "M3 11l9-7 9 7M5 10v10h5v-6h4v6h5V10"
    static let tabSound = "M5 4v6M5 14v6M12 4v3M12 11v9M19 4v9M19 17v3" + SVG.circle(5, 12, 2) + SVG.circle(12, 9, 2) + SVG.circle(19, 15, 2)
    static let tabRooms = "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z"
    static let tabSettings = SVG.circle(12, 12, 3) + "M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"
}
