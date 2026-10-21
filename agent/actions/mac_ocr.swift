import Vision
import AppKit
import CoreGraphics
import Foundation

func click(x: CGFloat, y: CGFloat) {
    let pt = CGPoint(x: x, y: y)
    for t in [CGEventType.mouseMoved, .leftMouseDown, .leftMouseUp] {
        let ev = CGEvent(mouseEventSource: nil, mouseType: t,
                         mouseCursorPosition: pt, mouseButton: .left)!
        ev.post(tap: .cghidEventTap)
        Thread.sleep(forTimeInterval: 0.06)
    }
}

let args = CommandLine.arguments
// usage: mac_ocr <image_path> click <text> | mac_ocr <image_path> digits
guard args.count >= 3 else {
    print("usage: mac_ocr <image> click <text> | mac_ocr <image> digits")
    exit(1)
}
let imagePath = args[1]
let mode = args[2]
let target = args.count >= 4 ? args[3] : ""

guard let nsimg = NSImage(contentsOfFile: imagePath),
      let cg = nsimg.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    print("noload"); exit(1)
}

guard let screen = NSScreen.main else { print("noscreen"); exit(1) }
let sw = screen.frame.width
let sh = screen.frame.height

let req = VNRecognizeTextRequest()
req.recognitionLevel = .accurate
req.recognitionLanguages = ["zh-Hans", "en-US"]
let handler = VNImageRequestHandler(cgImage: cg, options: [:])
try? handler.perform([req])

if mode == "click" {
    for obs in (req.results ?? []) {
        guard let c = obs.topCandidates(1).first else { continue }
        if c.string.contains(target) {
            let b = obs.boundingBox
            let x = b.midX * sw
            let y = (1 - b.midY) * sh
            click(x: x, y: y)
            print("clicked:\(Int(x)):\(Int(y))")
            exit(0)
        }
    }
    print("notfound")
} else if mode == "dump" {
    var out = ""
    for obs in (req.results ?? []) {
        if let c = obs.topCandidates(1).first { out += c.string + "\n" }
    }
    print(out)
    exit(0)
} else if mode == "digits" {
    var all = ""
    for obs in (req.results ?? []) {
        if let c = obs.topCandidates(1).first { all += c.string + " " }
    }
    let digits = all.components(separatedBy: CharacterSet.decimalDigits.inverted).joined()
    let regex = try! NSRegularExpression(pattern: "\\d{8,11}", options: [])
    let ns = digits as NSString
    if let m = regex.firstMatch(in: digits, options: [], range: NSRange(location: 0, length: ns.length)) {
        print(ns.substring(with: m.range))
        exit(0)
    }
    print("nodigits")
} else {
    print("badmode")
}
