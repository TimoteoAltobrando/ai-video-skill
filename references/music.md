# Music and sound effects

## Contents
1. When
2. The composition plan
3. Generating and choosing
4. Aligning and putting it in the edit
5. Fixes on the file
6. Sound effects
7. Drops and accents on the animations
8. Under a voice
9. Mix and master

## 1. When

Generate the music when the animated draft is approved and the scene timings are stable. The music follows the
scenes, not the other way round. Before that, work with temporary effects (keystrokes, clicks): they already give the
rhythm. Nobody in the loop can listen except the user: say so, give them the measures, and let them decide by ear.

## 2. The composition plan

One music section per scene (or group of scenes), with durations in whole bars: at 120 BPM a bar lasts 2 s.

An example structure for 48 s of music (the full template is in `assets/templates/music-plan.json`):

| Section | Time | In the film | Character |
|---|---|---|---|
| Intro | 0-10 s | the problem, the first action | suspended, few elements, dark; no kick |
| Build | 10-20 s | the product starts working | sub hit on the first beat, kick and syncopated bass, rising |
| Swell | 20-24 s | the pieces come together | it widens, a noise riser towards the end |
| Breath | 24-30 s | the result, the key click | filtered, low level, a held sub note |
| Groove | 30-42 s | it runs again and again | full: bass at maximum, claps on 2 and 4, fast hi-hats |
| Outro | 42-48 s | logo and line | one big final hit (chord plus sub), then a tail to silence |

For a **narrative film with a speaker** (about 2 minutes), the sections follow the story instead: the problem
(sparse, tense) → a stop on the key word → the question (a sparse arpeggio) → the work begins (drums enter) → the
reveal (the biggest hit, full) → what changes (a steady groove under the voice) → a break before the manifesto → the
peak → a "brake" (a tape stop on the word) → the restart → the logo chord → (a short, light coda under a final
call-to-action page).

How to write each section:
- `text`: the section name in square brackets, then the direction in curly brackets. For example
  `[Groove: Runs again]\n{full groove hits right on the first beat…}`.
- `positive_styles`: genre, `instrumental`, `120 BPM`, the key (for example `A minor`), the instruments and what
  happens, and "on the first beat" when a change must fall exactly there.
- `negative_styles`: `vocals`, `choir`, `spoken word`, `EDM drop`, `dubstep wobble`, `fade-out ending`… (voices are
  excluded this way, because `force_instrumental` cannot be used with a plan).
- `context_adherence`: how much the section imitates its neighbours. `low` where the music must change at once (the
  kick coming in, a breath, a restart, the ending); `medium` or `high` where it must carry on.

Typical requests: "more bass, more engaging" = deep sub, a full dry kick, a syncopated bass, a little pumping
compression, claps on 2 and 4, sixteenth-note hi-hats. "A hybrid orchestral trailer" (strings, brass, trailer drums,
taiko, piano and celesta) suits a speaker well.

## 3. Generating and choosing

- Generate 2-4 versions with different seeds (the seed is the number that makes a generation repeatable):
  `scripts/elevenlabs.py music --plan … --seed N`. Keep count of the credits.
- When the user is undecided between styles, make 2-3 different plans (for example cinematic electronic, electro-pop,
  hybrid orchestral) on the same structure, and send one file that plays them one after the other with a spoken
  label. Then refine the chosen one instead of starting again.
- Measure each one with `scripts/measure_music.py`, by section:
  - when the kick comes in;
  - the energy below 60 and below 120 Hz;
  - the level and the brightness;
  - the tempo and the key.
  Choose the one whose section boundaries are in the right place.
- **Check the key on the bass.** The estimate from the chromagram (the average of the notes over the whole track) can
  be wrong (it can say C♯ minor while the bass always plays A, and effects tuned to C♯ are then out of tune). `measure_music.py` prints the most frequent low notes for each section: the key is the one the bass repeats.
- The model tends to put changes on 8-bar phrases rather than where you ask, to keep builds flat, to make weak endings
  and to change key. If after 3-4 generations something does not work, fix it on the file or in the edit (sections 5
  and 7). A new generation can also change the sound the user liked: when they chose a sound, keep that generation
  and add what is missing around it.

## 4. Aligning and putting it in the edit

- `scripts/prepare_bed.py raw.wav bed.wav --bpm 120 --duration 48 --lufs -16`:
  - trims the start so that the first beat falls at 0;
  - brings the file to the exact duration;
  - sets the loudness to −16 LUFS (perceived loudness), with the true peak below −1 dBTP.
- Check the measured tempo: if it is more than 0.05% away from 120 BPM, over 50 s the beats drift. Then a small speed
  correction is needed.
- In the edit the bed can start later (for example after 2 s of keystrokes only): the simplest way to fit an existing
  structure to longer scenes.
- **With a speaker the cuts follow the voice, so the music is fitted to the cuts**: choose the cuts that matter (the
  start, the stops, the reveal, the peak, the logo: 15-25 of them) and build a tempo map that puts a whole beat on
  each. Between two fixed points stretch the music uniformly, beat by beat (by sixteenths above ~1.8%), with the
  splices about 24 ms before an onset and 16 ms crossfades where the two waves are most alike. Up to ±2.7% is not
  heard; the attacks land within a quarter of a frame. Change the tempo only at a stop or at a section start.
- **Lengthening a section** (for example the groove, because a scene grew): repeat "clean" bars from the middle of
  the section, respecting the progression (if bars alternate two by two, repeat them in pairs), with 10-15 ms fades
  before the beat. **Never repeat the last bar before a change**: it usually holds the fill that announces the end,
  and repeating it makes a stutter ("announce, restart, announce again"). Check the joins with the level per bar and
  the spectrogram.
- **Risers** must end exactly on the hit they lead to (the first beat of the next section, the explosion, the logo).
  A riser that ends a moment early, or on any beat, sounds detached. Scene exits also start on the beat.
- **Edit silences:** bringing the music to zero on the click before the restart (one second of silence, then the full
  rhythm) is very effective.

## 5. Fixes on the file

- **Flat build:** apply a low-pass filter that opens, for example from 700 Hz to fully open, plus a volume ramp from
  −4 to 0 dB. Work in blocks with crossfades, so there are no clicks; check with the spectrogram that the edge of the
  highs rises diagonally.
- **Look first at what the generated ending contains.** Measure the strongest low note every half second: if it keeps
  falling or rising (a descent like a slowing tape), or changes key, do not lift it and do not use it. Such a tail,
  raised, sounds like a break.
- **An ending rebuilt "on the hit":** cut the bed at the end of the transition bar and put in its place the first beat
  of the groove taken from the track itself (kick, bass, chord: already in the right key), one on the explosion and a
  slightly softer one on the logo. Under each hit: a synthetic reverb (noise fading in 4-5 s, band 180-6000 Hz, about
  8 dB below the hit) and a sub note on the tonic (for A: 55 Hz plus the octave), then a fade that ends before the end
  of the film. Use a fixed seed for the noise, so the file is rebuilt identically. Do not add the falling sub hit
  there: the low end is already in the music.
- **A final hit that is only weak but clean** (it stays on the tonic): lift the tail in the edit (×2-×3, watching the
  peaks) and add a sub hit.
- **Wrong key for pitched effects:** transpose the effects (beeps, notes, small 8-bit motifs) to the key of the music.
  Do not touch the music.
- **A coda for an extra page** (a call to action after the logo): continue the logo chord (hold its first beat), a
  short riser into the page, a light rhythm from a quiet section of the same track (raised carefully: check the
  noise), an accent on the page's main event, a last hit that dies exactly on the last frame.

## 6. Sound effects

- **Real ones, with ElevenLabs:** soft keystrokes, a mechanical click, paper (a burst of tiles, a sheet laid down), a
  rustle, a dull thud, a brick snapping in, a relay, a tick. Generate clean single hits, "dry, close, isolated".
- **Synthetic ones**, with ffmpeg (`aevalsrc`) or Python:
  - beeps and small 8-bit motifs (square wave), tuned to the key of the music;
  - `sub-hit`: a sine falling from 90 to 38 Hz, 3 ms attack with a small transient, 1.2 s tail (good for entrances and
    restarts; on the ending a steady note on the tonic is better);
  - `noise-riser`: 2 s of noise with a filter rising from 250 Hz to 9 kHz, cut sharply at the end, placed so that it
    ends exactly on the change.
- **Where to put them:**
  - one effect for each visual event: keystrokes, files landing, clicks, check marks, dives (a whoosh), screen splits
    (a brick);
  - sub hits on a scene entering, the rhythm restarting, the explosion and the logo;
  - rising notes on a series of completions.
- **Indicative volumes:** keystrokes 0.3-0.5; strong hits 0.8-1; 8-bit notes 0.1-0.3.

## 7. Drops and accents on the animations

What "it must follow the motion, with nice drops" means in practice:
- **The effects are the map of the animations**: every effect sits on a movement. Export their list (frame of
  the hit, name, volume) and use it to put the musical accents on the strongest movements, not only on the cuts.
- **Drops** (the moment the music explodes after a build and an instant of emptiness): the biggest on the reveal, then
  the peak and the logo; smaller ones where a new section starts. Before each: a riser (noise, orchestra, pitch) and
  about half a beat of total silence (~250 ms); on the hit: an impact, a braam (the low, distorted trailer brass hit)
  and a sub falling to the tonic (for A: from 110 to 55 Hz); tune them to the key (transpose by semitones, estimating
  their note from the lowest strong frequency).
- **Accents:** reverse cymbals that grow and end sharply on a cut; sub hits on entrances; whooshes on fast moves; the
  music opening and closing (a filter) in time with a graphic that pulses; a stutter (a small piece repeated in a
  burst) before a drop — the most electronic touch over an orchestra, use it sparingly.
- **Do not double the effects**: if a musical hit falls on an effect that does the same job (a sub hit in the effects
  on the same frame as the drop's sub), lower or remove the effect. List them for the edit instead of guessing.
- If an important animation lands 2-4 frames off a beat, suggest moving the animation (and its effect) onto the beat;
  the user decides.

## 8. Under a voice

- **Ducking in three bands**: between 300 Hz and 4 kHz keep the voice about **11 dB above the music** in every sentence
  (14-17 dB in the quiet, delicate ones); leave the low end (kick, bass) more present, so the music still pushes.
  Attack 40 ms, release 450 ms; where the speaker is silent, the music comes back full. Bake it into the bed (a
  pre-ducked `bed.wav` placed from frame 0) so the edit stays simple.
- Measure understanding: transcribe voice plus music with whisper (`tools.md`) and count the words it gets right
  against the voice alone. A loss of 1-3% is normal; if a key word is lost, lower the music there.
- Where the speaker is silent the drops can be loud (momentary −10 to −13 LUFS against a voice at −16); on a hit
  under a word, keep the hit in the lows and the highs and dip only the mids, so the word stays clear.

## 9. Mix and master

- Measure the loudness by section and check that the effects do not cover the music (or the other way round) at the
  key points.
- `scripts/export.sh` brings everything to −14 LUFS integrated (the web and social standard) with a limiter on the
  peaks, and puts the audio exactly in sync with the picture.
- **When the user asks to lower the music** ("still too loud"), lower only the music and keep the master gain of the
  previous export (`FIXED_GAIN_DB`); re-normalising raises the voice and the effects and the change almost
  disappears. If the request also mentions the effects, ask whether they go down together (it is easy to read it the
  wrong way). Reasonable steps: −2 dB for "a hair", −4 to −6 dB for "clearly lower".
- Watch the limiter on the drops: 3-5 dB of reduction on the biggest hits is acceptable; much more flattens them.
- Remind whoever approves: the sub is heard on headphones or speakers, not on the phone's speaker.
