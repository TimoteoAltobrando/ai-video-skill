# Remotion: how the film is built

## Contents
1. Project structure
2. The time grid
3. Scenes and transitions
4. Video clips (Seedance) inside scenes
5. Interfaces, typing, camera
6. A person on camera: pieces, punch-ins, layers
7. Audio: bed, effects, voice
8. 3D and logo
9. Checking and rendering
10. Disk space and partial renders

## 1. Project structure

```
src/
  brand/        tokens (colours, curves), fonts, Logo.tsx with the paths of the official SVG
  common/       audio.ts (bed and effects), wipes, reused components
  film/
    index.ts    registerRoot
    Root.tsx    <Composition id="Film" …> (and the tests)
    timing.ts   FPS, DURATION, SCENES {name: {from, to}} and the internal timings of each scene
    texts.ts    ALL the text of the film (other languages too)
    Film.tsx    the edit: scenes, transitions, music, effects
    scenes/     one scene per file
public/         images, clips, audio, icons
docs/           brief, script, storyboards, spend
```

- Fonts are loaded with `@remotion/fonts` and `delayRender` / `continueRender` in the root, before rendering.
- Colours and curves come from the brand guidelines and live only in the tokens: never hand-written colours in the
  scenes.
- With footage, keep the edit decisions in one data file (for example `plan.json`: shots with `from`/`to`, which
  piece of the take each one uses and at what speed, subtitles with times, music sections, key hits), written by a
  script and read by the composition: every change of the cut moves everything consistently.

## 2. The time grid

- 24 frames per second with music at 120 BPM: **12 frames per beat, 48 per bar** (2 s). At 30 fps (phone footage):
  15 frames per beat, 60 per bar.
- Every scene starts on a whole bar; strong events fall on the beats, minor ones on the eighths.
- `timing.ts` is the only source of timings: `SCENES = { field: { from: 0, to: 288 }, … }` and, for each scene, the
  internal events (`KEY_CLICK = { at: 120, … }`). Music and effects read from there.
- If the music is already made and the edit changes, move the scenes by whole bars, or start the music later: never
  cut the music inside a chord progression. With a speaker the cuts follow the voice: then the music is fitted to the
  cuts instead (`music.md`).

## 3. Scenes and transitions

```tsx
// a scene that enters with a wipe over the previous one, which meanwhile keeps its own time
const Scene: React.FC<{ from: number; to: number; previous?: { node: React.ReactNode; from: number }; children: React.ReactNode }> =
  ({ from, to, previous, children }) => (
    <Sequence from={from} durationInFrames={to - from}>
      {previous ? (
        <Wipe outgoing={<Sequence from={-(from - previous.from)}>{previous.node}</Sequence>} incoming={children} />
      ) : children}
    </Sequence>
  );
```

- With the negative `from` the outgoing scene continues from where it was, and does not start again.
- Useful wipes: cells (tiles flipping diagonally or radially from a point, for example the button just pressed), a
  hard cut on the beat, a zoom into a brand element.
- **Continuity:** if the same object passes from one scene to the next, the last frame of the first and the first of
  the second must match to the pixel. Check it by rendering both frames and comparing them, for example with a
  difference in Python.

## 4. Video clips (Seedance) inside scenes

```tsx
<OffthreadVideo src={staticFile("film/clip-k1.mp4")} muted playbackRate={0.5} trimBefore={48} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
```

- `playbackRate` fits a 5 s clip to a longer scene (down to about 0.5; below that the motion stutters). `trimBefore`
  (in frames) starts the clip later.
- Several clips side by side (split screen) are boxes that contain the 1920×1080 video scaled to cover. The box is
  animated (splitting, diving in, coming back) by interpolating its rectangle.
- If a clip is too short, do not restart it: slow it down or pick another piece.

## 5. Interfaces, typing, camera

- **Interfaces:** real React components, with the product's real labels, the brand colours, the corners and borders of
  the guidelines. The mouse pointer (a drawn arrow) moves to the buttons, hovers and clicks on time.
- **Typing:**
  - type at a speed in characters per second: `n = floor((f - start) * cps / fps)`;
  - typing that speeds up uses a quadratic curve: `n = L * t²`;
  - "chat" answers arrive one word every 2 frames.
- **Camera on the interface:** translate and scale the whole layer towards the active field, with keyframes and a
  soft curve at the start of each stretch: `transform: translate(960 - cx*s, 540 - cy*s) scale(s)` with
  `transformOrigin: 0 0`. Fixed elements (for example a column of steps) stay outside this layer; if the camera would
  cover them, hide them in that stretch.
- **Key words over video:** large (90-110 px), in the brand typeface, word by word from below inside a mask, with a
  soft dark veil behind. No shadows, if the guidelines forbid them.
- All movements use the brand curves (for example `cubic-bezier(0.22, 1, 0.36, 1)` on the way out).

## 6. A person on camera: pieces, punch-ins, layers

- **Pieces:** each shot plays one or more continuous pieces of the take: `<Sequence from={piece.from}>` with
  `<OffthreadVideo src=… trimBefore={piece.take} playbackRate={piece.speed} muted />`. A slight slow-down (0.4-0.75)
  can stretch a pause without a visible cut; keep it rare.
- **Punch-ins:** scale 1.0 or ~1.3 framed on the face (measure the face position on the footage once):
  `transform: scale(s) translate(-cx, -cy)` with `transformOrigin: 0 0`, clamped so the frame never shows outside the
  picture.
- **Layers for graphics behind and in front of the person:**
  1. the room alone: the blurred empty room (`blur_background.py --blurred-plate`, as an `<Img>`; add a light animated
     grain) or a room-only video;
  2. graphics behind the person (`<ThreeCanvas>` with a transparent background, or HTML);
  3. the person: `<OffthreadVideo src="person.webm" transparent muted />` (VP9 WebM with alpha, from
     `blur_background.py --layer`). Without `transparent` the frames come out as JPEG and the alpha turns black;
  4. graphics in front.
- **Never** put the person layer over a video that already contains the person: the edges get composited twice and
  come out darker, a dark outline that reads as "cut out". Under the person's edge the background must be the empty
  room.
- The browser composites in signal space (not in linear light): a dark-over-bright edge comes out slightly darker
  than in a linear composite. A short alpha ramp and decontaminated edge colours (both done by
  `blur_background.py`) keep it invisible; a custom WebGL compositor can blend in linear light.
- **Check it with numbers** (`on-camera.md` section 10): render a frame and compare it with the Python composite in
  the edge band.
- Depth of field on 3D objects: keep them sharp for legibility; at most a little blur on objects far behind.

## 7. Audio: bed, effects, voice

```tsx
// the bed starts at frame 48 of the film; an edit silence before the restart
<Sequence from={48}>
  <Html5Audio src={staticFile("audio/bed.wav")} volume={(f) => (f >= 696 && f < 720 ? 0 : 1)} />
</Sequence>
// an effect: an <Html5Audio> inside a <Sequence from={at}> (at = film frame)
```

- Keep a registry of the effects (name → file, duration, where the "hit" is inside the file). Then
  `<Sfx name="click" at={264} />` lands the hit exactly on `at`, even if the file has a slow attack.
- Keystrokes go one per character, or one every two frames, with varied volumes; in fast bursts the volume goes down.
- The volume as a function of the frame is for hard silences and for lifting a music tail that is too weak.
- **A separate audio-only composition** (voice, music, effects, no pictures and no 3D) renders in a minute instead of
  evaluating every 3D frame, and lets you change the mix without re-rendering the picture: render it to WAV, master
  it, mux it with the silent picture (`delivery.md`).
- **Headroom:** Remotion sums the tracks into 16-bit PCM. With big drops the sum goes over full scale and clips
  before any limiter can help: scale all the volumes of the audio composition (for example ×0.75, −2.5 dB) and raise
  the gain in the master instead. `export.sh` warns when the rendered audio clips.
- **Changing one level:** to lower only the music (or only the effects), change that volume and keep the master gain
  of the previous export (`FIXED_GAIN_DB`): re-normalising to −14 LUFS would raise the voice and the effects and
  shrink the change.
- To get data out of the composition (for example the list of all effects with their frames, to align the music to
  the animations), export it from a small script or render a frame with `--log=verbose` and print it from the
  component: browser console messages only appear at verbose level.

## 8. 3D and logo

- `@remotion/three` with `ThreeCanvas`. For the brand's flat colours use materials without tone mapping (`flat`):
  with the default tone mapping bright colours fade.
- **Ending with the logo:** build the symbol in 3D (for example from many small pieces), bring the camera face-on in an
  orthographic view, that is without perspective, and on the landing frame replace the 3D with the official SVG.
  Render that frame both ways and compare them: the difference must be zero.
- If the ending starts from an object of the previous scene (an image), overlay the same image in the same position
  for the first 2-3 frames and fade it into the 3D.

## 9. Checking and rendering

```bash
npx tsc --noEmit                                                   # after every change
npx remotion bundle src/film/index.ts --out-dir /tmp/bundle          # once per round
npx remotion still /tmp/bundle Film out/f0288.png --frame=288 --scale=0.5
python3 scripts/contact_sheet.py --images out/f*.png --out out/sheet.jpg --columns 4
sh scripts/export.sh src/film/index.ts Film out/film.mp4           # full video, audio in sync, -14 LUFS, 720p copy
```

- Render the frames where something happens (start and end of each scene, events, joins) and look at them all in a
  sheet before exporting.
- If a render stops on an expired `delayRender` (it happens with video clips), re-run it with `--timeout=120000`: the
  export script already does.
- A full render of 50 s at 1080p takes about 1-2 minutes on a recent Mac; a 2-minute film with 3D around a speaker
  about 15 minutes.

## 10. Disk space and partial renders

- Every render (and every `bundle`) **copies the whole `public/` folder**, and the audio mix writes large temporary
  files in `$TMPDIR` (`remotion-*` folders, left behind by failed renders). A full disk shows up as confusing errors
  ("mergeAudioTrack…", "No space left on device"). Check `df -h` before rendering, keep only the files in use in
  `public/` (old versions stay in your work folders), delete leftover `remotion-*` temporary folders.
- **Partial renders:** when only the end changed, render only that range and splice it into the previous silent
  picture, re-encoding once:

```bash
npx remotion render src/film/index.ts Film tail.mp4 --frames=3733-4070 --muted
ffmpeg -i previous.mp4 -i tail.mp4 -filter_complex \
  "[0:v]trim=end_frame=3733,setpts=PTS-STARTPTS[a];[1:v]setpts=PTS-STARTPTS[b];[a][b]concat=n=2:v=1:a=0,format=yuv420p[v]" \
  -map "[v]" -c:v libx264 -preset medium -crf 16 -r 30 picture.mp4
```

  Then check the frame count and compare a frame before the join with the previous version.
