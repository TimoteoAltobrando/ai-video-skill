# Editing footage: from a pile of clips to a cut

How to edit footage the user already has: an event, a trip, highlights, interviews, podcast clips, a long recording
to shorten.

## Contents
1. Never touch the originals
2. Inventory: know what there is
3. Watching hours of footage without a video player
4. Make the footage workable
5. Selects and the paper edit
6. Story shapes for montages
7. Cutting
8. Assembling in Remotion
9. Colour
10. Sound
11. Vertical and other formats
12. Privacy in the footage

## 1. Never touch the originals

- Copy or link the originals into `footage/original/` and never write there. Every conversion goes to
  `footage/work/`. If something goes wrong, the original is still the original.
- Keep a list of which work file comes from which original, with the command that made it (in `docs/footage.md`).

## 2. Inventory: know what there is

```bash
python3 scripts/inventory.py footage/original --out docs/footage.md --sheets docs/sheets --every 5
```

One row per clip: duration, size, frame rate, codec, HDR, rotation, audio, date. Read it for the traps before cutting:
- **VFR** (variable frame rate, common on phones): convert to a constant rate first, or picture and sound drift apart
  in the edit.
- **HDR** (HLG or PQ): convert to SDR with `scripts/hdr_to_sdr.sh` (`on-camera.md` section 2).
- **Mixed frame rates** (25, 30, 60): choose the project rate (usually the most common one) and conform the rest;
  60 or 120 fps clips can become real slow motion (section 7).
- **Rotation** flags and **missing audio**.
- **Dates**: the creation date orders a chronological montage; it can be wrong (time zones, copied files).

## 3. Watching hours of footage without a video player

You cannot watch video in real time, but you can look at frames and read speech:
- **Contact sheets** (`--sheets`): one frame every few seconds per clip. For long clips use a larger `--every`, then
  denser sheets only on the interesting stretches (`scripts/contact_sheet.py --video clip.mp4 --frames …`).
- **Cuts inside a clip** (`--scenes 0.35`): a long file that was already edited, or a phone left recording.
- **Speech**: transcribe every clip with people talking (whisper, `tools.md` section 9) to text with times. The
  transcript is how you find "the moment she thanks the team" or the three best answers of an interview.
- **Loud moments**: applause, laughter, the music at a party show up as peaks in the loudness over time
  (`ffmpeg -af ebur128` prints the momentary loudness); they are often the moments worth keeping.
- **Sharpness and shake**: shaky or blurred stretches are visible in the sheets; mark them as unusable.
- Say clearly to the user what you looked at and how: "I looked at one frame every 5 seconds and read the
  transcripts". Ask them for the moments that matter emotionally: you cannot know who the bride's grandmother is.

## 4. Make the footage workable

- Convert to constant frame rate and SDR, H.264 with a keyframe every second (fast and exact seeking in Remotion):
  ```bash
  ffmpeg -i in.mov -vf fps=30 -c:v libx264 -crf 16 -g 30 -pix_fmt yuv420p -c:a aac -b:a 256k -ar 48000 out.mp4
  ```
- **Proxies**: with many hours of 4K, make 720p copies to look at and cut, and render the final from the full files.
- **Stabilise** shaky handheld shots only if needed (two passes with ffmpeg's `vidstabdetect` and `vidstabtransform`,
  if ffmpeg has libvidstab); it crops the frame a little.
- Check the disk: converted footage is often larger than the original (`remotion.md` section 10).

## 5. Selects and the paper edit

Before assembling anything, write the cut on paper (`docs/edit.md`, template `assets/templates/edit.md`):
1. **Selects**: every usable moment, with clip, in and out time, what we see, what we hear, and a mark (★ best,
   ○ usable). Usually 3-5 times more material than the final length.
2. **The paper edit**: the selects in order, with the length of each, the sections of the story and the music
   sections. Add up the times: it must fit the agreed length.
3. **Show it**: the paper edit with a contact sheet (one frame per shot, in order) and the open questions. The user
   approves the order before you assemble: moving a line costs nothing, re-rendering costs minutes.

## 6. Story shapes for montages

- **Chronological**: the day as it happened (arrival → main moments → the end); add a strong shot at the very start as
  a hook, then go back to the beginning.
- **Best moments arc**: open strong (a striking image or a big moment), build with variety, a peak (the emotional or
  loudest moment), a calm ending (a wide shot, a look, a smile), a title or logo.
- **By theme**: people, places, details, action; each group a music section.
- **Around a speech**: a voice (a speech, an interview, a toast) carries the story; the footage illustrates it (cutaways
  over the voice) and comes back to the speaker on the strongest sentences.
- **Short vertical**: the result or the peak in the first second, then how we got there, then the call to action.

## 7. Cutting

- **Shot length**: in a montage on music, cut on the beat (every bar or every half bar), longer shots in calm
  sections, shorter at the peak. Never shorter than about 0.7 s unless it is a deliberate burst.
- **Cut on action**: a movement that starts in one shot and finishes in the next hides the cut.
- **Variety**: alternate wide, medium and close shots; avoid two similar shots in a row (a jump).
- **Speech**: cut between sentences, not inside words; let the sound lead or follow the picture by a few frames
  (J and L cuts: we hear the next person just before we see them) to make dialogue flow. Cover the jumps in a
  talk with a cutaway or a punch-in (`on-camera.md` section 12).
- **Slow motion**: real slow motion only from high-frame-rate clips (a 60 fps clip played at 30 fps is half speed,
  clean). Invented frames (`minterpolate`) make artefacts on people: avoid them, or use them only for short moments
  and look at the frames.
- **Speed ramps** and freeze frames: few, on the music accents.

## 8. Assembling in Remotion

- One `<Series.Sequence>` per shot from the paper edit, with `<OffthreadVideo>` and its in and out points
  (`trimBefore`/`trimAfter` in recent Remotion versions, `startFrom`/`endAt` in older ones), all timings in
  `timing.ts` generated from `docs/edit.md`, so the paper edit and the film never disagree.
- Titles, lower thirds, captions and transitions as Remotion components (`remotion.md`).
- Render the key frames of every shot into a contact sheet and check the in and out points: a shot that starts on a
  blink or a camera bump must move by a few frames.
- For very long, simple edits (hours of conference talks to cut into clips) ffmpeg alone can be enough: cut with
  re-encoding (not `-c copy`, which cuts only on keyframes), then join with the concat demuxer.

## 9. Colour

- One look for the whole film, chosen on 3-4 frames from different clips (show them side by side before and after).
- First **match** the clips (white balance and exposure: shots of the same place must look the same), then apply the
  **look** (contrast, warmth, saturation) to everything. With ffmpeg: `eq`, `colorbalance`, `colortemperature`, or a
  LUT (`lut3d`) if the user has one.
- Skin tones are the test: never orange, never grey.
- Phone footage of the same event from different people has different colours: matching matters more than the look.

## 10. Sound

- **Ambient sound** gives life to a montage: keep it low under the music (about −20 to −25 dB below the music) and
  bring it up on the moments that matter (laughter, a cheer, a sentence).
- **Speech** clean and understandable: the voice clean-up and the ducking of the music are in `on-camera.md`
  section 3 and `music.md` section 8.
- **Wind and handling noise**: a high-pass filter (around 80-100 Hz) and cutting the worst stretches; a noisy shot can
  run without its sound under the music.
- **Room tone**: when cutting speech, fill gaps with a few seconds of the same room's silence, not digital silence.
- **Music rights**: a song the user likes is not a song they can publish; on social platforms add licensed trending
  sounds in the platform's own app.
- Master at −14 LUFS with `scripts/export.sh` (`music.md` section 9).

## 11. Vertical and other formats

- Reframe each shot, not the whole film with one crop: the subject moves. Keyframe the crop position per shot
  (follow the face or the action); `scripts/person_mask.swift` gives the person's position frame by frame if needed.
- Keep the platform's **safe area** free of text: on Reels, TikTok and Shorts the bottom and the right side are
  covered by the interface (`delivery.md` section 3).
- A wide shot that does not survive a 9:16 crop can sit on a blurred copy of itself, or be replaced by another select.

## 12. Privacy in the footage

- People who did not agree, minors in public posts, number plates, screens with personal data, documents on a desk:
  blur them, or choose another shot. Ask the user, do not decide alone.
- A blur that follows a moving face needs tracking; often it is simpler and safer to drop the shot.
- Location data and dates in file metadata go away in the export (`-map_metadata -1`).
