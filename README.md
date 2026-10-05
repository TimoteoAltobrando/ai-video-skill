# ai-video-skill

**Make and edit videos with Claude Opus 5.5.** A [Claude Code](https://claude.com/claude-code) skill, written and
tested with Opus 5.5, that takes a video from the first idea, or from your own footage, to the finished files: product and launch films, ads, talking-head and founder videos, interviews, explainers and
tutorials, event and trip montages, podcast clips, Reels/TikTok/Shorts, animated logos, music videos, and changes to a
finished video (a shorter cut, a vertical version, subtitles, a translation, new music).

Remotion is the backbone; images come from Codex (`image_gen`), AI animation from Seedance (via OpenRouter), music
and sound effects from ElevenLabs, footage and speech are handled with ffmpeg and whisper. Claude first asks what kind
of video it is and everything that kind needs, then proposes the direction, gets the script (or the paper edit of the
footage) approved piece by piece and produces the video, round after round, until delivery.

The references hold what makes a video work and what to avoid: direction, music, the person on camera, editing
footage, delivery for each platform.

## What it does

1. **Intake**: where we start from (from scratch, footage, both, a finished video), the kind of video, the platforms,
   the length; then the core (goal, audience, materials, voice, words, music, AI or not, rights and consent, budget)
   and the questions specific to that kind. A one-screen brief to confirm before any work.
2. **Tools and keys**: only those the chosen path needs, stored safely, with spending caps.
3. **Analysis**: brand, product, footage (inventory, contact sheets, transcripts), references.
4. **Direction**: story ideas with images and a script with one image per piece, or, for footage, the selects and
   a paper edit with one frame per shot; hooks for short verticals.
5. **The person on camera** (if any): the room, the light, the voice, the graphics around them; a shooting guide if it
   is not shot yet.
6. **Production** in Remotion, **revisions** and **delivery**: masters, phone copies, vertical cuts, platform notes,
   the end card and call to action, even the launch posts.

## Install

```bash
git clone https://github.com/TimoteoAltobrando/ai-video-skill ~/.claude/skills/ai-video
```

or copy the folder into `.claude/skills/` inside a project.

## How to use it

1. **Store your keys once** (optional, only for the services you use), from your own terminal. Each command asks for
   the key without showing it:
   ```bash
   security add-generic-password -a "$USER" -s elevenlabs-api-key -w     # music, sound effects, voice clean-up
   security add-generic-password -a "$USER" -s openrouter-api-key -w     # Seedance AI animation
   ```
2. **Open Claude Code in an empty folder** for the video and say what you want, for example: *"a 60-second launch
   video for [product]"*, *"I have 3 hours of our company event: make a 90-second highlight and a vertical teaser"*,
   or *"cut this webinar into five clips for LinkedIn with subtitles"*. The skill starts by itself (or ask for it by
   name: "use the ai-video skill").
3. **Answer the questions**: at most three short rounds, most of them multiple choice; every question has a default if
   you do not know.
4. **Approve the direction**: the script or the paper edit, piece by piece. Nothing is produced before you approve it.
5. **Review the drafts** (there is always a light copy for the phone) and ask for changes in plain words. Listen with
   headphones: Claude can look at frames but cannot hear.
6. **Get the files**: the master, the phone copy, the other formats, and notes on what was decided and spent.

Tips: one change at a time is faster than a long list; keep plenty of free disk (about three times the footage); say
your spending caps at the start.

## Requirements

- macOS is recommended: keys in the Keychain, HDR conversion with VideoToolbox, the person mask with Apple Vision. On
  Linux the keys go in environment variables and the footage tools need replacements.
- Node 18 or newer, ffmpeg (with `libvpx-vp9` and `libx265`), Python 3 with
  `numpy scipy soundfile librosa pillow opencv-python`.
- Codex CLI, installed and logged in (`codex login`), for the images.
- An ElevenLabs API key (music and effects) and an OpenRouter key with credit (Seedance), with a spending cap you
  decide. Both are optional if you bring your own music and do not need 3D clips.
- A Remotion licence if your company has more than 3 people (remotion.dev/license).
- 15-20 GB of free disk space for an animated film; with footage, about three times its size.
- For footage with speech: whisper.cpp (`brew install whisper-cpp`) and a model.

Keys are never pasted in the chat: Claude gives you the command to store them in the Keychain from your own terminal.

## What is inside

| Path | What |
|---|---|
| `SKILL.md` | the path, step by step (what Claude reads) |
| `references/intake.md` | the question tree by kind of video, the defaults, the brief to confirm |
| `references/editing.md` | editing footage: inventory, selects, paper edit, cutting, colour, sound, reframing, privacy |
| `references/direction.md` | principles, lessons, words on screen, narrative films, the revisions that always come |
| `references/on-camera.md` | the person on camera: questions, footage, voice, room and light, mask, blur, perspective, compositing |
| `references/tools.md` | setup, keys, Codex, Seedance, ElevenLabs, ffmpeg, whisper |
| `references/remotion.md` | how the film is built in Remotion, layers, audio, partial renders, disk space |
| `references/music.md` | composition plans, choosing by measures, tempo maps, drops and accents, ducking, mastering |
| `references/delivery.md` | files, phone limits, platforms, call to action, launch posts, final checklist |
| `scripts/` | `inventory.py`, `seedance.py`, `elevenlabs.py`, `measure_music.py`, `prepare_bed.py`, `codex_image.sh`, `contact_sheet.py`, `export.sh`, `hdr_to_sdr.sh`, `person_mask.swift`, `clean_plate.py`, `blur_background.py`, `wall_perspective.py` |
| `assets/templates/` | brief, script, paper edit, image prompt, an example music plan |

## Costs, roughly

Seedance via OpenRouter: about 0.09 $/s at 720p with the fast model, about 0.38 $/s at 1080p (September 2026). An
ElevenLabs music generation: about 1,800 credits for 48 s, about 5,600 for 2:26. Check the current prices.

## Limits

Claude cannot listen: music and voice choices are made with measures and then by the user's ear. Image and video
models change quickly: the model names and prices in the documents are those that were current in September 2026.

## Contributing

Issues and pull requests are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md). The maintainer reviews every proposal
and decides what goes into the skill.

## License

[MIT](LICENSE) © 2026 Timoteo Altobrando
