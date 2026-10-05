---
name: ai-video
description: Make and edit videos with Claude Opus 5.5, end to end, from a blank page or from the user's own footage — product and launch films, ads, talking-head and founder videos, interviews, explainers, tutorials and screen demos, event and trip montages, highlight reels, podcast clips, Reels/TikTok/Shorts, animated logos and intros, music and lyric videos, and changes to a finished video (shorter cut, vertical version, subtitles, translation, new music). Remotion is the backbone; Codex (image_gen) makes images, Seedance via OpenRouter animates them, ElevenLabs makes music and sound effects, ffmpeg and whisper handle footage and speech. It starts by asking what kind of video it is and everything that kind needs (platform, format, voice, music, rights, who must not appear, budget), then goes through direction, a script or paper edit approved piece by piece, production, revisions and delivery for each platform. Use it whenever someone wants to make, cut, edit, shorten, reformat, subtitle or improve a video, even if they do not mention any of these tools.
---

# AI video: make and edit videos with Claude Opus 5.5

This skill takes a video from the first idea, or from a pile of footage, to the finished files along one path:
**intake → materials and keys → analysis → direction → script or paper edit → (person on camera) → production →
revisions → delivery**. The references in `references/` hold the principles, the recipes and the mistakes to avoid for each part of
the work.

Talk to the user in their language. Explain technical terms the first time you use them. Keep answers short and
concrete: the user must always know where we are and what we need from them. You can look at frames but you cannot
hear: say so when a choice is made by ear, and let the user choose.

## Golden rules

1. **Clear first, beautiful second.** Someone watching without sound must understand what the video is about. No
   abstract metaphors to decode, no titles that explain: it is understood from what happens.
2. **Real facts.** Screens, labels, numbers, names, places and dates come from real sources (the product, the
   footage, the user), not from imagination. Never a promise or a number nobody can back. AI images never fake real
   people, products or places.
3. **Ask before you work, approve before you produce.** The intake comes first (`references/intake.md`). Then the
   script (or the paper edit for footage) piece by piece, with one image or frame per piece. Only what is approved
   gets animated or assembled.
4. **One decision at a time, written down.** Every approved choice goes in `docs/script.md` or `docs/edit.md`. Never
   treat as approved what the user did not say. When a request is ambiguous about its scope, ask before doing the
   work.
5. **Rights and consent.** Recognisable people agreed to appear; the music can be published where the video goes;
   other companies' logos only from official files. Who must not appear is asked at the start, not after the cut.
6. **Exact brand.** The logo only from the official files; an animated logo lands on the official SVG to the pixel;
   brand colours exact. If the brand changes during the work, update it everywhere.
7. **Continuity and rhythm.** The same object carries on from one scene to the next; events and cuts fall on the
   music grid. The music is made or cut on the edit, not the other way round.
8. **Physics.** Anything added to real footage obeys the real camera: perspective, light direction, shadows, scale,
   depth of field.
9. **Keys and money.** Keys live in the Keychain (or in environment variables) and are never printed or written to
   files. Every expense is logged and stays under the agreed cap.
10. **Check with your eyes, and measure.** After every change render the key frames into a contact sheet and look at
    it before sending anything; measure what can be measured (loudness, sync, subtitles against the voice). Send
    drafts often, also as a light copy for the phone. The originals of the user's footage are never modified.

## Phase 0 · Intake: what kind of video (questions)

Read `references/intake.md` and follow it. In short:
1. **Round 1** (question tool, one call): where we start from (from scratch · footage to edit · both · a finished
   video to change), the kind of video, where it will be watched, how long.
2. **Round 2**, the core for every video: the goal in one sentence, the audience, the materials (paths and links),
   names and words to write exactly, deadline and approver; voice, words on screen, music, the use of AI images;
   rights and consent; the budget.
3. **Round 3**, the module of the chosen kind (product, person on camera, explainer, montage, short vertical, logo,
   music video, change to a finished video).
4. **The brief back**: `docs/brief.md` in one screen, "Is it right? Anything missing?", and the gate checklist of
   `intake.md` section 6. Do not start the analysis with a "must" still open.

Skip every question the request already answers; give a default for every question (`intake.md` section 5).

## Phase 1 · Tools and keys

Only for what the chosen path uses (details and commands in `references/tools.md`):
- ElevenLabs (music, effects, voice isolation): an API key and a credit cap.
- OpenRouter (Seedance, AI animation): a key and a spending cap.
- Codex CLI (images): installed and logged in.
- Remotion: free for individuals and companies of up to 3 people; above that a company licence.
- whisper (speech to text), for footage with speech and for checking subtitles.

Never ask for keys to be pasted in chat: give the command to store them in the Keychain from their own terminal and
then check that the scripts can read them. If a key is pasted anyway, store it at once, never repeat it, and suggest
regenerating it.

Then check by yourself: `node`, `ffmpeg`, `python3` (and `codex`, `swiftc`, `whisper-cli` if the path needs them);
free disk space (15-20 GB for an animated film, 30-40 GB or more with footage: about three times the size of the
footage); the Python environment (`references/tools.md`). If something is missing, say so with the command to fix it.

## Phase 2 · Analysis (no questions)

Read, look at and transcribe everything, then complete `docs/brief.md`.
- **Brand guidelines**, if any: colours, typefaces, motion curves, logo rules, forbidden things, tone of voice.
- **Product** (kind A and C): the real path, step by step, with the exact labels; verified facts apart from claims.
- **Footage** (whenever there is any): `scripts/inventory.py` for the table and one contact sheet per clip, the
  transcripts of speech, the traps (variable frame rate, HDR, rotation, mixed rates). See `references/editing.md`
  sections 2-3, and `references/on-camera.md` when a person speaks to camera.
- **References**: frames, a contact sheet, and what makes them work (text, rhythm, cuts, music).
- **Competitors or similar videos**, if useful and if web search is available.

Close with a five-line summary: what you understood, what you saw in the footage, what doubts remain.

## Phase 3 · Direction (questions)

**Created videos** (from scratch, or graphics around footage):
1. **2-3 story ideas**, each in 5-7 beats with duration, visual character and music character, with 1-2 Codex images
   each in a contact sheet. Ask which one, or what to mix.
2. **Visual style**: if undecided, two or three directions on the same beat.
3. **Script**: `docs/script.md` from `assets/templates/script.md`, a table of pieces with time, what we see, words on
   screen, medium and one storyboard image per piece (`scripts/codex_image.sh`). With a speaker, the script is
   narration, not explanation. Read `references/direction.md` first.

**Edited footage**:
1. **The shape**: 2 story shapes for this footage (`editing.md` section 6), each with the sections and their length.
2. **Selects and paper edit**: `docs/edit.md` from `assets/templates/edit.md`, with a contact sheet of one frame per
   shot in order. Ask for the moments that matter to them: you cannot know who is who.

**Short verticals**: 3 hooks for the first second, shown as frames, before the rest.

**Approval piece by piece** in every case: correct until the user says it is fine.

## Phase 3b · The person on camera: room, light, voice (questions)

Only if someone speaks on camera. Read `references/on-camera.md` first: it has the questions, the options with their
risks, the recipes, and a shooting guide if the footage does not exist yet. Ask in one round (closed choices with the
question tool): the room (keep, blur, dress, replace, with the risks), blur strength, light, style of the place, brand
in the room, the voice (clean-up, slips, re-recording), graphics around the person.

Then: proposals of the **empty room** first, **3-4 test frames with the person**, and only then the whole take.

## Phase 4 · Production

Read `references/remotion.md` before writing code and `references/music.md` before touching audio; with footage also
`references/editing.md`, with a person on camera `references/on-camera.md`.

1. **Remotion project.** The project frame rate (24 for a fully animated film, otherwise the footage's own rate,
   usually 30), the chosen format, a music grid (at 120 BPM: 12 frames per beat at 24 fps, 15 at 30 fps). Timings in
   `timing.ts` (generated from `docs/edit.md` for footage), texts in `texts.ts`, brand tokens in their own file.
2. **Footage**: work copies in constant frame rate and SDR, proxies for long 4K material, the originals untouched
   (`editing.md` section 4).
3. **Images** with Codex, always with the same reference image for one style. Texts and logos are never drawn by AI.
4. **AI animation** with Seedance (`scripts/seedance.py`) only where it helps: the fast 720p model first, 1080p for
   the main shots, `--log docs/spend.md --cap <dollars>` on every call.
5. **The person on camera**: HDR conversion, person mask, empty room, then the chosen room (`on-camera.md`).
6. **Scenes and assembly**: interfaces as real components, shots from the paper edit with exact in and out points,
   titles, lower thirds, captions; colour matched then graded (`editing.md` section 9).
7. **First draft** with temporary sound: render, contact sheet, look, then send the draft and the light copy.
8. **Music and sound** when the timings are stable: generated on the sections (2-4 takes, chosen by measures and then
   by the user's ear) or the user's track cut on whole bars; ambient sound and voice mixed under it; effects on the
   events (`music.md`).
9. **Export** with `scripts/export.sh`: audio in sync, mastered at −14 LUFS (the standard perceived loudness for web
   and social), plus the light copy.

## Phase 5 · Revisions

Every round: apply the changes; check the types (`npx tsc --noEmit`); render and look at the touched frames (only the
changed range if the rest is final); export; send the video with two lines on what changed and what is still open.

Typical requests are in `references/direction.md` ("Revisions that always come"), `references/on-camera.md` and
`references/editing.md`. Move music or scenes by whole bars. If only the music level changes, keep the master gain
fixed (`FIXED_GAIN_DB`), otherwise the voice and the effects move too.

## Phase 6 · Delivery

Read `references/delivery.md`: the master, a light copy, a phone copy under the upload limit, the other formats and
lengths agreed; platform notes (length limits, burned-in subtitles and automatic captions off, safe areas on
verticals, the cover); the end card and the call to action; `docs/` with every decision and expense. Before
delivering: no keys or personal paths in the files, official logos, measured loudness, subtitles checked against the
voice, metadata (location, dates) removed if the user wants.

## Where to find what

| File | When to read it |
|---|---|
| `references/intake.md` | At the start of every project: the question tree, the defaults, the gate |
| `references/direction.md` | Before a script and at every revision: principles, words on screen, typical revisions |
| `references/editing.md` | Whenever there is footage to edit: inventory, selects, paper edit, cutting, colour, sound, reframing, privacy |
| `references/on-camera.md` | When a person speaks on camera: questions, shooting guide, voice, room and light, mask, compositing |
| `references/tools.md` | Phase 1 and whenever you use Codex, Seedance, ElevenLabs, ffmpeg, whisper |
| `references/remotion.md` | Before writing the Remotion project |
| `references/music.md` | Before generating or cutting music and effects, and for the mix |
| `references/delivery.md` | Exports, phone limits, platforms, vertical safe areas, call to action, launch posts |
| `scripts/` | `inventory.py`, `contact_sheet.py`, `codex_image.sh`, `seedance.py`, `elevenlabs.py`, `measure_music.py`, `prepare_bed.py`, `export.sh`, and for a person on camera `hdr_to_sdr.sh`, `person_mask.swift`, `clean_plate.py`, `blur_background.py`, `wall_perspective.py` (instructions at the top of each file) |
| `assets/templates/` | `brief.md`, `script.md`, `edit.md` (selects and paper edit), `image-prompt.md`, `music-plan.json` |
