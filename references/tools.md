# Tools: setup, keys and recipes

## Contents
1. Keys (macOS Keychain)
2. First check
3. Remotion
4. Codex: images
5. Seedance via OpenRouter: animations
6. ElevenLabs: music and effects
7. ffmpeg: frames, light copies, loudness
8. Footage: HDR, person mask, empty room
9. whisper: checking subtitles against the voice
10. Original file-type icons

## 1. Keys (macOS Keychain)

Keys never go through the chat and never end up in a file. The user stores them from their own terminal; the
command asks for the key without showing it and without leaving it in the shell history:

```bash
security add-generic-password -a "$USER" -s elevenlabs-api-key -w
security add-generic-password -a "$USER" -s openrouter-api-key -w
```

The scripts read them by themselves (`security find-generic-password -s <service> -w`). They also accept the
environment variables `ELEVENLABS_API_KEY` and `OPENROUTER_API_KEY`: use them on Linux or without a Keychain.

To replace a key, delete the old one first: `security delete-generic-password -s <service>`.

Errors already seen:
- the key ID mistaken for the key itself (ElevenLabs answers `api_key_id_used_as_api_key`);
- OpenRouter credits exhausted (HTTP 402): top up, or use another key.

## 2. First check

```bash
node -v && npx -v              # Remotion: Node 18 or newer
ffmpeg -version | head -1      # ffmpeg (if missing: brew install ffmpeg); libvpx-vp9 is needed for alpha video
python3 --version
codex --version                # Codex CLI, logged in (codex login)
swiftc --version               # macOS only, for scripts/person_mask.swift
df -h .                        # 15-20 GB free (30-40 GB with long footage)
```

Python environment for audio measures, contact sheets and image work, created once:

```bash
python3 -m venv .venv && .venv/bin/pip install numpy scipy soundfile librosa pillow opencv-python
```

## 3. Remotion

- **Licence.** Remotion is free for individuals and for companies of up to 3 people; above that a company licence is
  needed (remotion.dev/license). Ask before you start.
- **New project.** `npx create-video@latest`, blank TypeScript template. Keep all `remotion` and `@remotion/*`
  versions identical.
- **3D.** Use `@remotion/three` with `three` and `@react-three/fiber`. On macOS WebGL without ANGLE renders blank; in
  `remotion.config.ts`:

  ```ts
  import { Config } from "@remotion/cli/config";
  Config.setChromiumOpenGlRenderer("angle");
  Config.setVideoImageFormat("jpeg");
  Config.setJpegQuality(95);
  ```

- The rest of the working methods is in `remotion.md`.

## 4. Codex: images

Codex CLI generates images with its `image_gen` tool. Use `scripts/codex_image.sh`:

```bash
sh scripts/codex_image.sh docs/boards p1-start                    # reads docs/boards/prompt-p1-start.md
sh scripts/codex_image.sh docs/boards k2-world reference.png      # same style as a reference image
```

- The prompt file asks to generate **one** image and save it with the exact name (`p1-start.png`) in the folder. The
  template is `assets/templates/image-prompt.md`.
- About 1-2 minutes per image; several can run in parallel.
- The Codex model is passed with `-m` (variable `CODEX_MODEL`). In some setups image generation does not start
  without the right model: try a simple image first and write down the model that works.
- To keep the same style across many images, always pass the same reference image (`-i`) and repeat the style
  constraints in the prompt: light, colours, materials, camera.
- **On real footage** (a room to dress): give Codex a real empty frame (`clean_plate.py`) and ask to add only the
  listed objects and keep everything else identical; then align the result to the real frame (`on-camera.md`).
- Texts, logos and sharp interfaces are not asked of the images: they are composed in Remotion. If an image comes out
  with writing, titles or wrong backgrounds, regenerate it with tighter constraints ("no text, no letters, no
  logos…").

## 5. Seedance via OpenRouter: animations

`scripts/seedance.py` animates an image (first frame), and optionally the arrival (last frame), into a clip of about
5 s:

```bash
python3 scripts/seedance.py --first k1.png --prompt "slow dolly-in, small figures carry objects across the scene, soft light" \
  --out clip-k1.mp4 --model bytedance/seedance-2.0-fast --resolution 720p --log docs/spend.md --cap 15
python3 scripts/seedance.py --first k1.png --last k2.png --prompt "..." --out clip.mp4 --estimate   # cost only
```

- **Costs** (September 2026, check openrouter.ai): `seedance-2.0-fast` at 720p about 0.09 $/s (0.46 $ for 5 s);
  `seedance-2.0` at 1080p about 0.38 $/s (1.9 $ for 5 s). Try the fast model, then redo in 1080p only the main shots.
- **Spending cap.** Agree it in phase 1 and check the total of `docs/spend.md` before every call. The script prints
  the estimate and, with `--log`, appends a row with the real cost.
- **What works:** slow, simple camera moves, small characters doing repetitive actions, stable light. First and last
  frame together keep the geometry still.
- **What does not work:** texts, logos and symbols (they melt), scene changes inside the clip, many objects
  transforming. Check the end of the clips: the geometry often "slides" there and odd flares appear. Cut or slow down
  that part.
- In Remotion clips are fitted to the scenes with `playbackRate` and `trimBefore` (see `remotion.md`).

## 6. ElevenLabs: music and effects

`scripts/elevenlabs.py`:

```bash
python3 scripts/elevenlabs.py credits
python3 scripts/elevenlabs.py music --plan docs/music-plan.json --seed 1 --out audio/raw/bed-s1.wav
python3 scripts/elevenlabs.py sfx --text "single soft low-profile keyboard keystroke, dry, close" --duration 0.5 --out audio/sfx/key.wav
```

- **Music:** model `music_v2_5` with a composition plan (`composition_plan`), a list of sections with duration,
  text and styles. Each section lasts 3 to 120 s. With a plan `force_instrumental` cannot be used: voices are excluded
  in the negative styles. Indicative cost: about 1,800 credits for 48 s, about 5,600 for 146 s. How to write the plan
  is in `music.md`.
- **Effects:** model `eleven_text_to_sound_v2` (`/v1/sound-generation`), with duration and `prompt_influence` (0-1,
  how literally to follow the text). Short, concrete descriptions work best ("dry, close, isolated, no room noise").
  For single hits generate several variants and keep the cleanest.
- **Credits:** agree a cap; the script logs the credits each call used (if other jobs share the account at the same
  time, the number includes theirs).
- The output is PCM at 48 kHz: the script converts it to WAV.

## 7. ffmpeg: frames, light copies, loudness

```bash
# one frame (number 240 at 24 fps) from a video
ffmpeg -v error -ss $(python3 -c "print(240/24+0.001)") -i film.mp4 -frames:v 1 f0240.png
# light 720p copy for the phone (about 5-6 MB for 50 s)
ffmpeg -v error -i film.mp4 -vf scale=1280:720 -c:v libx264 -preset slow -crf 25 -pix_fmt yuv420p \
  -c:a aac -b:a 192k -movflags +faststart film-720p.mp4
# perceived loudness (integrated LUFS) and true peak
ffmpeg -hide_banner -nostats -i film.mp4 -af ebur128=peak=true -f null - 2>&1 | tail -12
```

- **Contact sheet:** `scripts/contact_sheet.py` puts chosen frames of a video, or a set of images, in one image.
- **Late audio:** Remotion 4's default mp4 (AAC) plays about 43 ms after the picture. `scripts/export.sh` renders the
  picture without audio, the audio as WAV (exact), masters and muxes everything with ffmpeg: the delay is gone.
- **Seeking to an exact frame** in a stream read by a script: `-ss (n - 0.5)/fps` before `-i` and `-frames:v`. With
  VP9 WebM (millisecond timestamps) ffmpeg may warn about repeated timestamps in the raw output: the frames are still
  the right ones (check once against a read that counts frames from the start).
- Phone and platform limits are in `delivery.md`.

## 8. Footage: HDR, person mask, empty room

```bash
sh scripts/hdr_to_sdr.sh IMG_0001.mov take.mp4 30                 # add --noautorotate if the picture is sideways
swiftc -O scripts/person_mask.swift -o person_mask                # once (macOS)
./person_mask take.mp4 | ffmpeg -v error -f rawvideo -pix_fmt gray -s 1920x1080 -r 30 -i - -c:v ffv1 mask.mkv
python3 scripts/clean_plate.py --video take.mp4 --mask mask.mkv --out plate.png --coverage coverage.png
python3 scripts/blur_background.py --video take.mp4 --mask mask.mkv --plate plate.png --test 900 --test-out t900.png
python3 scripts/blur_background.py --video take.mp4 --mask mask.mkv --plate plate.png --out room.mp4 \
  --layer person.webm --blurred-plate room-blurred.png
python3 scripts/wall_perspective.py segments plate.png --out lines.png --json lines.json
```

Speeds measured on a recent Apple-silicon laptop: person mask ~50 ms per frame; clean plate ~20 s for a 2-minute take;
blurred room ~0.2 s per frame per process (4 processes in parallel, plus the encoders). The whys and the numbers are
in `on-camera.md`.

## 9. whisper: checking subtitles against the voice

whisper (OpenAI's speech-to-text, run locally with whisper.cpp: `brew install whisper-cpp` and a model such as
`ggml-large-v3-turbo`) is an impartial ear:

```bash
ffmpeg -v error -i voice.wav -ac 1 -ar 16000 voice16.wav
whisper-cli -m ggml-large-v3-turbo-q5_0.bin -f voice16.wav -l en -ml 1 -sow -osrt -of words   # one word per line, with times
```

Compare, for each subtitle, the words spoken between its start and end with the subtitle text. Names are usually
misheard by whisper; for small doubtful words cut the sentence out and transcribe it alone with a wider search
(`-bs 8 -bo 8`). Use it also to check that the voice stays understandable under the music.

## 10. Original file-type icons

For PDF, Word, Excel, PowerPoint and images, Microsoft's official file-type icons (the ones of OneDrive and
SharePoint) are instantly recognised. The exact address comes from the npm package `@fluentui/react-file-type-icons`:
`DEFAULT_BASE_URL` in `lib-commonjs/initializeFileTypeIcons.js`; the icons are at `<base>96/<type>.svg`, with type
`docx`, `xlsx`, `pptx`, `pdf`, `photo`, `csv`, `txt`, `zip` and others.

```bash
npm view @fluentui/react-file-type-icons dist.tarball     # download the package and read DEFAULT_BASE_URL
curl -sfL -o public/file-icons/docx.svg "<base>96/docx.svg"
```

They are Microsoft trademarks and the assets have their own licence terms: read them, and for paid advertising have
the use checked.
