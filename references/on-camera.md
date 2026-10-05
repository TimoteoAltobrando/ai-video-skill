# The person on camera: room, light, voice, mask

How to turn footage of a person speaking to camera, often shot on a phone in an ordinary room, into a film that
looks professional. Read it before you touch the footage: the expensive mistakes are listed here, with how to avoid
them.

## Contents
1. The questions to ask
2. The footage
3. The voice
4. The room: options and risks
5. Light
6. The person mask
7. The blurred room (portrait look)
8. Dressing the room
9. Perspective and physics
10. Compositing in Remotion without the cut-out look
11. Graphics around the person
12. Editing a talking-head film
13. If the person still looks cut out
14. If it has not been shot yet: a shooting guide

## 1. The questions to ask

Ask before processing anything, in one round, and offer the options with their risks (the user decides; you
recommend). Closed choices go in the question tool:

| Topic | Question | Options (recommended first) |
|---|---|---|
| Room | What do we do with the room behind them? | blur it like a portrait lens · keep it, only a better grade · dress it (a few objects, a framed print) · replace it |
| Blur | How much? | clear portrait look · subtle · none |
| Light | What light do you want? | warm and bright · neutral · cool · moody; a visible lamp "making" the light? |
| Face | Can we correct the light on the face? | only a global grade (safe) · a light on the person (risk: cut-out look) |
| Place | What kind of place should it feel like? | modern office · almost luxury · minimal · home · industrial; ask for reference images |
| Brand | Should the brand be in the room? | a framed print with the logo or icon in the exact brand colour · objects in brand colours · nothing |
| Voice | How do we treat the voice? | cleaned (several versions to choose by ear) · as recorded; slips fixed only in the subtitles · re-record some lines |
| Graphics | What appears around them? | glass cards and 3D objects behind and in front · lower third with name and title · a credentials slab · nothing |

Then show, in this order:
1. **proposals of the empty room** (no person), generated with Codex on a real frame: quick to judge, cheap to
   change. People decide the room much faster without the person in front of it;
2. **3-4 test frames with the person**, at different moments (a still moment, a wide gesture, the head turning);
3. only then **the whole take**.

Write the answers in `docs/script.md`. When the user reacts with a feeling ("it looks fake", "it's cold", "they look
cut out"), find the cause before changing things: section 13 lists the usual ones.

## 2. The footage

- **HDR.** iPhones record HDR (HLG or Dolby Vision, 10 bit, BT.2020). Remotion and the platforms work in SDR BT.709:
  unconverted HDR looks flat and washed out, and a wrong conversion burns the whites or turns the skin orange. Convert
  with Apple's own pipeline (VideoToolbox), like Photos and iMovie do: `scripts/hdr_to_sdr.sh in.mov out.mp4 30`.
  The ffmpeg `colorspace` filter does not know HLG.
- **Rotation.** Some clips carry a wrong rotation flag: look at one frame. If the picture comes out sideways, use
  `--noautorotate`. The person mask (`person_mask.swift`) is always in the stored orientation: keep both the same.
- **Frame rate.** Keep the footage rate (often 30 fps) for the whole project: the music grid becomes 15 frames per
  beat at 120 BPM.
- **Tripod.** A clean empty-room plate and a blurred room need a still camera. Measure the drift on a static area
  (ECC alignment between the first and the last frame): up to 1-2 px over minutes is fine; more, and you must align
  every frame to a reference before making the plate.
- **Long takes.** Process in chunks with several processes, and watch the disk: a 2-minute take produces several
  GB of intermediate files.

## 3. The voice

- **Clean-up options**: a voice isolation service (ElevenLabs, by minute of audio), the phone or Mac's own voice
  processing, filters (high-pass, de-reverb, gentle compression), or a version the user made themselves. Mixing two
  of them (for example 75% of one and 25% of another) can remove the "robotic" feel of a single process.
- **Let them choose by ear**: put 5-8 versions of the same 20 seconds one after the other in one file, with a short
  spoken or written label, and ask for the number. You cannot hear: never pick for them.
- **Keep it in sync**: any processed voice must be aligned to the original track (cross-correlation), or the lips
  drift. Bring the chosen voice to about −16 LUFS before the mix.
- **Pronunciation slips**: the usual decision is to keep them and write the correct words only in the subtitles and
  in the on-screen texts that were planned anyway, without adding graphics just to correct. Re-recording lines is
  possible (same phone, same room, same distance) but rarely worth it. Do not "repair" a real person's voice with
  a synthetic one unless they explicitly agree.
- **Silences**: cut moments where the person is on screen and says nothing. Cut the voice with a 10 ms crossfade and
  move everything after it (subtitles, music map, sound effects) by the same amount.

## 4. The room: options and risks

| Option | What it is | Risk | When |
|---|---|---|---|
| **Blur** | the real room, blurred like a portrait lens, the person sharp | the safest; hides small flaws; looks premium | the default recommendation |
| **Keep + grade** | the real room with a global grade (warmer, brighter) | an ordinary room stays ordinary | the room is already nice |
| **Dress** | a few added objects or a framed print, the real pixels around the person | added objects can look fake; light and perspective must match | the room is bare |
| **Replace** | a different room | needs a perfect mask; light and perspective never match fully | almost never with phone footage |

Avoid:
- **Repainting the wall behind the person** (a new colour): every imperfection of the mask becomes a halo, and
  objects in front of the wall get an outline. Viewers read it as "everything looks fake, even the real
  parts". Do not change the colour of the real wall behind a person.
- **Objects pasted one by one** (plants, books, a lamp) from separate generations: each with its own light, they
  look "too fake".
- **A light change only on the person** (brighter face, darker room through the mask): a sharp mask edge looks cut
  out, a soft one leaves a halo on a plain wall.

Prefer:
- **A coherent dressed plate**: Codex on a real empty frame, asked to add only a few things and keep everything else,
  the image aligned to the real room, and the real pixels kept in the zone the person ever covers. Blurred, it
  looks natural.
- **The blurred real room** with the person untouched: the most natural result, and usually what people choose
  once they see it next to the alternatives.

## 5. Light

- "More professional" usually means **warmer and brighter**, with the face clearly brighter than the wall. A visible
  warm lamp (a practical) justifies a warm grade.
- Prefer **one grade on the whole frame** (white balance, exposure, contrast, a soft shoulder on the highlights) to
  any correction through the mask.
- With a blurred room, keep the room about **−0.3 EV** below the person: the face stands out without any mask.
- Brand colour light from the graphics (a glass card glowing in the brand colour on the wall) works as a faint glow in "screen"
  blend on bright surfaces only. A tint multiplied over the whole room colours the objects too (a brown object
  turns blue).

## 6. The person mask

- `scripts/person_mask.swift` (macOS, Apple Vision, person segmentation in "accurate" quality, about 50 ms per
  frame): free, local, good. Its edge is soft and lower resolution than the video, and it sometimes attaches nearby
  objects (a chair, something on the desk) to the person.
- **Refinement with the clean plate** (when the edge matters, for example over a dressed room): the deep inside of
  the Vision mask (eroded ~12 px) is always person, the outside of the dilated mask is always room, and in the band
  between them the colour difference between the frame and the clean plate decides.
- **Temporal stability**: average the mask over the 7 neighbouring frames, but each neighbour only where the image
  did not change by more than ~4 levels out of 255. Where the person is still the edge stops trembling; where they
  move (hands) it stays the frame's own, without trails. A plain 3-frame average does not help.
- **Glasses**: the lenses that stick out of the profile show the wall through them: keep them semi-transparent, or a
  light reflection of the old wall stays visible near the temple.
- **Fast hands**: leave the motion blur as it is; do not average the mask where there is motion.

## 7. The blurred room (portrait look)

`scripts/blur_background.py` does the whole recipe. The parts, and the numbers to start from:
- **Disk blur in linear light**, not Gaussian: highlights become soft bright discs, not grey smudges. Radius 13 px at
  1080p for a wall ~2.5 m behind a person ~1 m from the camera. A 1.3x punch-in in the edit makes it ~17 px, like a
  longer lens: that is right.
- **Strong highlights boosted before the blur** (up to 4x above 0.93): lamps and lit shelf strips bloom like through
  a real lens.
- **The person's edge**: the faint veil of the mask below 0.10 removed with a short ramp; within 2.5 px of the outline
  the person's colour taken from inside the figure (no light rim from the old wall); a gentle light wrap of the
  blurred room into the outline (normal blend at 0.10: the screen blend often recommended makes a white rim on a
  bright wall).
- **Grain**: the blurred room has no grain, the person has the phone's. Measure the grain on a flat area of the real
  wall (high-pass std per channel, typically 0.002-0.004) and add the same grain to the room, changing every frame.
- **Brand objects in the blurred room** (a logo on a print) are blurred separately with premultiplied alpha and in
  their exact colour, after the room's exposure change: otherwise the brand colour shifts.
- Outputs: the composite (person on room) for direct use, and the person alone with alpha plus the blurred empty
  room for layering graphics between them (section 10).

## 8. Dressing the room

- Generate on the **empty plate** (clean_plate.py), not on a frame with the person: Codex gets the scale from the room.
  Ask to add only the listed objects and keep everything else identical. Make 3-4 attempts and pick one.
- **Align** the generated image to the real plate: feature matches (SIFT or ORB) + RANSAC homography + ECC refinement,
  under 1 px of error.
- **Colours**: bring the generated parts to the light of the real room with a smooth gain field estimated where the two
  agree; never the other way round (the real wall is not changed).
- **Keep the real pixels** where the person ever goes during the take (the coverage map of clean_plate.py), so no
  generated object ever touches them.
- **A framed print with the logo**: do not let the model draw the logo. Draw the canvas and the frame yourself (or
  take Codex's empty frame), put the official logo in its exact colour, place it with the real perspective
  (`scripts/wall_perspective.py`) and add a soft contact shadow.

## 9. Perspective and physics

- A phone is rarely square to the wall: it is a little rotated (2-3° is common) and the wall a little oblique. Door
  frames lean, horizontal lines converge, a desk edge "rises". Anything flat added to the wall must follow the same
  vanishing points, or the user will say "it does not follow physics".
- `scripts/wall_perspective.py segments` lists the straight lines; pick the trusted ones (door frames and wall corners
  for the verticals; lintels, shelf edges and the desk-wall line for the horizontals) and `place` the object. Check
  the image it writes: the object's edges must follow the vanishing lines.
- Lamps and shelves drawn by an image model are often slightly off too. After the blur, small errors (1-2°) vanish;
  a large flat rectangle (a painting) never hides them.
- Also physics: shadows fall the way the room's light falls, sizes are believable (a print, a lamp), and objects at
  the wall's distance get the wall's blur.

## 10. Compositing in Remotion without the cut-out look

- **Layers**, from the back: the room (blurred plate or room-only video) → graphics behind the person → the person
  with alpha → graphics in front. In Remotion use `<OffthreadVideo transparent muted>` for the VP9 WebM with alpha:
  without `transparent` frames come out as JPEG and the alpha turns black.
- **Never put the person layer on top of a video that already contains the person.** At the edges the person is
  composited twice and comes out darker: a dark rim, exactly the cut-out look. Under the person's edge the background
  must be the empty room.
- **Blend in linear light** when you write your own compositor (WebGL, three.js): the browser composites in signal
  space, which darkens a dark-over-bright edge by up to ~20 levels at alpha 0.5.
- **Verify with numbers**: render a frame in Remotion and compare it with the same frame composited in Python, inside
  the person (alpha > 0.99), in the edge band (0.2 < alpha < 0.8) and in the room. Differences around the grain
  (≤ 5 levels of 255) are invisible; −18 in the edge band is a visible dark outline.
- If a renderer decodes the alpha layer with a different transfer curve than the room video, the person's colour shifts
  inside the figure: compensate (`blur_background.py --layer-gamma-fix` exists for this) and verify
  again. Do not apply it blindly.

## 11. Graphics around the person

- **Glass cards and 3D objects** around the speaker (in the style of modern AI launch films): behind them, in front
  of them, or passing from behind to the front, using the person's alpha. Frosted glass behind the person shows the
  empty room, blurred more.
- **Keep graphics sharp** even if the room is blurred: they must be read. A real depth of field on them looks
  physical but kills legibility; at most a hint on far objects.
- **Lower third**: name and title written exactly as the person wants (ask). A logo next to the company name is
  fine (official file).
- **Credentials slab** ("previously at …"): official logos of each company, roles shortened to fit, wording confirmed
  with the person. Public profiles can be out of date (a past job still listed as current): ask, do not guess.
- Keep the subtitle area and the face free; when a graphic says the same sentence big, hide that subtitle.
- **A curve or line that exits its card** must be designed for it: an exit improvised at the end looked broken.

## 12. Editing a talking-head film

- **The script is narration, not explanation**: first person, a story (problem → question → what we built →
  reveal → what changes → the line to remember). Product details go on screen, not into the sentences
  (`direction.md`).
- **Punch-ins** (1.0x and ~1.3x on the face) hide cuts and give rhythm; frame on the face position measured on the
  footage.
- **Subtitles burned in** (most people watch muted): short lines, broken at phrase boundaries (not "more / than
  100"), hidden where the same words are written big on screen. Slips are corrected only here.
- **Check the subtitles against the voice**: transcribe the voice with whisper and compare sentence by sentence.
  Names are usually misheard by whisper, not wrong in the subtitles; the real differences are small words ("the" vs
  "their", "a software"). Fix the subtitles where the person said something correct, keep the corrections where the
  person made a slip.
- **The end**: logo card, then a separate call-to-action page (for example "Join the waitlist" and the address, big,
  5 seconds) if the film is a launch. Ask before squeezing a button into the logo card.

## 13. If the person still looks cut out

Check the causes in this order:
1. **A light or dark rim on the outline**: no edge decontamination, or the person composited twice (section 10).
2. **A soft halo around them**: the mask is feathered too much. A sharp edge with a 1-2 px ramp and a light wrap is
   better.
3. **Different sharpness**: a sharp room behind a sharp, matted person looks like a collage. Blur the room like a lens.
4. **Different grain**: one grain over everything, changing every frame.
5. **Different light**: the same grade family on room and person, no light masks; a light wrap from the room.
6. **A trembling edge**: the motion-weighted temporal average of the mask (section 6).
7. **Everything static**: a slow camera drift with parallax (the room moves about half as much as the person) adds
   depth.

## 14. If it has not been shot yet: a shooting guide

Send this to the user before they shoot: an hour of preparation saves days of fixing.
- **Camera**: the phone's main (1x) lens, or a camera, on a tripod or a stable surface, at eye height, 1-1.5 m from
  the person. Horizontal for 16:9, vertical for 9:16; if both are needed, horizontal 4K with room around the person.
- **Settings**: 4K, 30 fps (25 in countries with 50 Hz mains if lights flicker), **HDR off** (SDR saves a conversion
  and its risks), exposure and focus locked on the face.
- **Light**: the face towards a window or a soft lamp, never a window behind the person; no overhead light alone.
- **Room**: a few metres between the person and the wall (it blurs better), nothing distracting behind, no screens
  with personal data in shot.
- **Sound**: a clip-on microphone (lavalier) if possible, otherwise the phone close; a quiet room without echo
  (curtains, a sofa, books help); notifications off. Record **10 seconds of silence** in the room at the end (room
  tone, to fill gaps in the edit).
- **Takes**: short sections rather than one long take; say again a sentence that went wrong, from the start of the
  sentence. A teleprompter app helps with a written script.
- Send the original files (AirDrop, cable, a shared folder), not files compressed by a messaging app.
