// Person mask for a whole video (or a stretch of it) with Apple Vision (person segmentation, accurate quality).
// macOS 12 or later. It reads the frames with AVFoundation (BGRA, BT.709: macOS maps HDR to SDR, enough for Vision),
// computes the mask, scales it to the output size and writes grey 8-bit bytes to standard output, one frame after
// the other: pipe them into ffmpeg, which stores them losslessly.
//
// Build once:  swiftc -O person_mask.swift -o person_mask
// Use:         ./person_mask <video> [start_s] [duration_s] [WIDTHxHEIGHT] \
//                | ffmpeg -f rawvideo -pix_fmt gray -s 1920x1080 -r 30 -i - -c:v ffv1 mask.mkv
//
// The output size defaults to the stored size of the video track. The mask is in the STORED orientation (like
// ffmpeg -noautorotate): if your clip relies on a rotation flag, rotate the mask the same way as the picture.
// Timing goes to standard error. Vision's mask is soft and lower resolution than the video: refine it before you
// composite (see blur_background.py and references/on-camera.md).
import AVFoundation
import CoreImage
import Vision

let args = CommandLine.arguments
guard args.count > 1 else {
    FileHandle.standardError.write("usage: person_mask <video> [start_s] [duration_s] [WIDTHxHEIGHT]\n".data(using: .utf8)!)
    exit(1)
}
let asset = AVURLAsset(url: URL(fileURLWithPath: args[1]))
let start = args.count > 2 ? Double(args[2])! : 0
let duration = args.count > 3 ? Double(args[3])! : 1e6
let sem = DispatchSemaphore(value: 0)
var trackOpt: AVAssetTrack?
var natural = CGSize(width: 1920, height: 1080)
Task {
    trackOpt = try? await asset.loadTracks(withMediaType: .video).first
    if let t = trackOpt, let s = try? await t.load(.naturalSize) { natural = s }
    sem.signal()
}
sem.wait()
guard let track = trackOpt else {
    FileHandle.standardError.write("no video track\n".data(using: .utf8)!)
    exit(1)
}
var W = Int(natural.width), H = Int(natural.height)
if args.count > 4 {
    let p = args[4].split(separator: "x").compactMap { Int($0) }
    if p.count == 2 { W = p[0]; H = p[1] }
}
let reader = try! AVAssetReader(asset: asset)
let output = AVAssetReaderTrackOutput(track: track, outputSettings: [
    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
    AVVideoColorPropertiesKey: [AVVideoColorPrimariesKey: AVVideoColorPrimaries_ITU_R_709_2,
                                AVVideoTransferFunctionKey: AVVideoTransferFunction_ITU_R_709_2,
                                AVVideoYCbCrMatrixKey: AVVideoYCbCrMatrix_ITU_R_709_2]])
output.alwaysCopiesSampleData = false
reader.add(output)
reader.timeRange = CMTimeRange(start: CMTime(seconds: start, preferredTimescale: 30000),
                               duration: duration > 1e5 ? .positiveInfinity : CMTime(seconds: duration, preferredTimescale: 30000))
reader.startReading()

let ctx = CIContext(options: [.workingColorSpace: NSNull(), .outputColorSpace: NSNull()])
let request = VNGeneratePersonSegmentationRequest()
request.qualityLevel = .accurate
request.outputPixelFormat = kCVPixelFormatType_OneComponent8
let sequence = VNSequenceRequestHandler()
var buf = [UInt8](repeating: 0, count: W * H)
let stdout = FileHandle.standardOutput
var n = 0
var tVision = 0.0
let t0 = Date()
while let sample = output.copyNextSampleBuffer() {
    guard let pixels = CMSampleBufferGetImageBuffer(sample) else { continue }
    let t1 = Date()
    try? sequence.perform([request], on: pixels)
    tVision += Date().timeIntervalSince(t1)
    if let m = request.results?.first?.pixelBuffer {
        var im = CIImage(cvPixelBuffer: m)
        im = im.transformed(by: CGAffineTransform(scaleX: CGFloat(W) / im.extent.width, y: CGFloat(H) / im.extent.height))
        ctx.render(im, toBitmap: &buf, rowBytes: W, bounds: CGRect(x: 0, y: 0, width: W, height: H), format: .L8, colorSpace: nil)
    } else {
        for i in 0..<buf.count { buf[i] = 0 }
    }
    stdout.write(Data(buf))
    n += 1
}
let total = Date().timeIntervalSince(t0)
FileHandle.standardError.write(String(format: "%d frames %dx%d in %.1f s (%.1f ms per frame, Vision %.1f ms)\n",
                                      n, W, H, total, total / Double(max(n, 1)) * 1000, tVision / Double(max(n, 1)) * 1000).data(using: .utf8)!)
