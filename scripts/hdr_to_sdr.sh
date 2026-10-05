#!/bin/sh
# Convert iPhone HDR footage (HLG / Dolby Vision, 10 bit, BT.2020) to SDR BT.709 the way Apple Photos and iMovie do,
# with VideoToolbox (macOS only). Remotion and the social platforms work in SDR: unconverted HDR looks flat and washed
# out, and the generic ffmpeg `colorspace` filter gets HLG wrong (burnt whites, orange skin).
#
#   sh hdr_to_sdr.sh input.mov output.mp4 [fps] [--noautorotate]
#
# fps: output frame rate (default 30, constant).
# --noautorotate: ignore the rotation stored in the file. Some phone clips carry a wrong rotation flag (the picture
# comes out sideways or upside down): look at one frame first, and add this flag if it is wrong.
# Output: H.264 CRF 14 (a working master, not for upload), keyframe every second, original audio copied.
set -e
IN="$1"; OUT="$2"; FPS="${3:-30}"
ROT=""
for a in "$@"; do [ "$a" = "--noautorotate" ] && ROT="-noautorotate"; done
case "$FPS" in --*) FPS=30;; esac
ffmpeg -v error -y -hwaccel videotoolbox -hwaccel_output_format videotoolbox_vld $ROT -i "$IN" \
  -map 0:v:0 -map "0:a:0?" -map_metadata -1 \
  -vf "scale_vt=color_matrix=bt709:color_primaries=bt709:color_transfer=bt709,hwdownload,format=p010le,scale=out_range=tv,format=yuv420p" \
  -fps_mode cfr -r "$FPS" -c:v libx264 -preset slow -crf 14 -g "$FPS" -bf 2 -pix_fmt yuv420p \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv \
  -c:a copy -movflags +faststart "$OUT"
echo "-> $OUT"
