#!/bin/sh
# Export a Remotion composition with the audio in sync and mastered, plus a light 720p copy.
#
#   sh export.sh <entry.ts> <CompositionId> <output.mp4> [more remotion options, e.g. --frames=0-47]
#   FIXED_GAIN_DB=4.5 sh export.sh ...      # reuse the master gain of a previous export instead of re-normalising
#
# Why it works this way:
# - Remotion 4's default mp4 (AAC) plays about 43 ms after the picture: here the picture is rendered without audio,
#   the audio as WAV (exact), and ffmpeg muxes the two with the right priming (zero delay);
# - the audio is brought to -14 LUFS integrated (the web and social standard) with a limiter at -1.5 dBFS, so the
#   true peak stays around -1 dBTP;
# - when only the music (or only the effects) changes, re-normalising to -14 LUFS raises everything else: the voice
#   and the effects get louder and the change you asked for shrinks. Pass FIXED_GAIN_DB with the gain printed by the
#   previous export to keep the voice exactly where it was;
# - Remotion sums all the audio tracks into 16-bit PCM: if loud moments go over full scale they are clipped before
#   the limiter can help. The script counts clipped samples and warns: lower the volumes in the composition (e.g. all
#   tracks x0.75) and raise the gain here instead;
# - --timeout=120000: with video clips a frame is sometimes late and the render would stop.
# Outputs: <output.mp4> (high quality, AAC 320k) and <output>-720p.mp4 (for the phone, about 5-6 MB per 50 s).
set -e
ENTRY="$1"; ID="$2"; OUT="$3"; shift 3
TMP="$(mktemp -d)"
npx remotion render "$ENTRY" "$ID" "$TMP/video.mp4" --crf=18 --muted --timeout=120000 "$@"
npx remotion render "$ENTRY" "$ID" "$TMP/audio.wav" --codec=wav --timeout=120000 "$@"
python3 - "$TMP/audio.wav" <<'EOF'
import sys, wave, array
w = wave.open(sys.argv[1])
if w.getsampwidth() == 2:
    a = array.array("h", w.readframes(w.getnframes()))
    n = sum(1 for v in a if v >= 32766 or v <= -32767)
    if n:
        print(f"WARNING: {n} clipped samples in the rendered audio: lower the volumes in the composition and re-export")
EOF
measure() { ffmpeg -hide_banner -nostats -i "$1" -af ebur128=peak=true -f null - 2>&1 | awk '/Summary:/{s=1} s&&/ I:/{i=$2} s&&/Peak:/{p=$2} END{print i, p}'; }
set -- $(measure "$TMP/audio.wav")
if [ -n "$FIXED_GAIN_DB" ]; then G="$FIXED_GAIN_DB"; else G=$(python3 -c "print(round(-14.0 - ($1), 2))"); fi
echo "audio before: $1 LUFS, true peak $2 dBTP; gain $G dB (reuse it with FIXED_GAIN_DB=$G)"
ffmpeg -v error -y -i "$TMP/audio.wav" -af "volume=${G}dB,alimiter=limit=0.84:attack=1:release=60:level=false" -c:a pcm_s24le "$TMP/audio-m.wav"
set -- $(measure "$TMP/audio-m.wav")
echo "audio after: $1 LUFS, true peak $2 dBTP"
ffmpeg -v error -y -i "$TMP/video.mp4" -i "$TMP/audio-m.wav" -map 0:v -map 1:a -c:v copy -c:a aac -b:a 320k -shortest -movflags +faststart "$OUT"
LIGHT="${OUT%.mp4}-720p.mp4"
ffmpeg -v error -y -i "$OUT" -vf scale=1280:-2 -c:v libx264 -preset slow -crf 25 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart "$LIGHT"
rm -rf "$TMP"
echo "-> $OUT"
echo "-> $LIGHT"
