# Delivery: files, platforms, launch

## Contents
1. The files to deliver
2. Sending to a phone
3. Platforms
4. The end card and the call to action
5. Launch posts and comments
6. Final checklist

## 1. The files to deliver

- **Master**: 1920×1080 (or the chosen format), the project frame rate, H.264 High, yuv420p, BT.709, AAC 256-320 kbit/s
  48 kHz, −14 LUFS integrated, true peak below −1 dBTP, `+faststart`. This is the file to upload to the platforms.
- **Light copy**: 720p (or 960×540) for quick review.
- **Phone copy in high quality**: 1080p under the phone upload limit (section 2).
- If requested: vertical (9:16) and square (1:1) cuts, versions in other languages, a version without subtitles.
- Name the versions with a number (`draft5.mp4`, `draft5-phone.mp4`) and write in `docs/script.md` what changed in each.

## 2. Sending to a phone

- Sending files to the user's phone usually accepts at most **30 MB**, and large files can time out on a slow
  connection even below that. The full master (often 60-100 MB for 2 minutes) is then visible only on the computer:
  say so and give the path.
- For high quality on the phone, re-encode the master at 1080p with **HEVC in two passes** at a target size (it keeps
  the quality much better than H.264 at the same size; iPhones play it natively):

```bash
# target ~28 MB for 135 s: (28 * 8 * 1024 * 1024 / 135) bit/s minus the audio ≈ 1500 kbit/s of video
ffmpeg -y -i master.mp4 -c:v libx265 -preset fast -b:v 1500k -x265-params pass=1:stats=x265.log -an -f null /dev/null
ffmpeg -y -i master.mp4 -c:v libx265 -preset fast -b:v 1500k -x265-params pass=2:stats=x265.log -tag:v hvc1 \
  -c:a aac -b:a 160k -movflags +faststart master-1080p-phone.mp4
```

  Compare one frame with the master (a face and a smooth gradient): at this size it should look almost the same.
- For drafts, a 960×540 or 720p H.264 copy at CRF 25-27 (5-8 MB for 2 minutes) arrives always.

## 3. Platforms

- **Upload the video natively** (not a link to another site): it plays in the feed, muted. That is why the subtitles
  are burned into the picture.
- **LinkedIn** adds automatic captions to uploaded videos; with subtitles already in the picture they overlap. Turn
  them off when uploading (the "auto captions" toggle), or remove them after posting: the "…" menu of the post → Edit
  captions → Remove captions (on the phone: tap a caption, the remove icon, Remove captions, Done). Everyone who
  posts the video (the company page, colleagues) must do it on their own post.
- **X** accepts videos up to 2:20 for standard accounts (longer with a paid plan): check the length before cutting. A
  post is limited to 280 characters without a paid plan: put the story in three short lines and the link in a second
  post of the same thread ("Add another post"), so it stays right under the first one.
- **Reels, TikTok and Shorts** (9:16, 1080×1920): the platform's interface covers the bottom (caption, buttons,
  about the lowest fifth of the frame) and a strip on the right (the like and share buttons); keep text and faces in
  the central area, roughly the middle 70% in height and away from the right edge. Check the current safe-area
  guides of each platform: they change. Most people watch muted: captions big, in the safe area.
- **Covers**: choose a strong frame as the cover (the call-to-action page or the logo card).
- Check that the platform does not crop the sides (a 16:9 video in a 4:5 feed shows black bars, not a crop; a vertical
  cut needs its own framing).

## 4. The end card and the call to action

- For a launch, after the logo card add **a separate page** (about 5 seconds) with the call to action written big:
  for example the site's main action ("Sign up", "Join the waitlist", "Book a demo") as its primary button (same shape, colours and type, larger) and the address
  in large type. A separate page reads better than a button squeezed into the logo card.
- A strong way in: the grid of the logo card floods with brand-coloured cells from the logo, and the page appears on
  the brand colour. Make the music continue under it (a short coda, `music.md`), with an accent when the address
  appears.
- **Check the real link** on the live site: the page may have its own path and language versions that do not follow
  the pattern you expect (for example `/page` for the default language and `/<language>/page` for the others, with no
  `/<default language>/page`). Open the exact link and use the one in the language of the post.

## 5. Launch posts and comments

People who publish the video often ask for help with the text:
- **A short narrative post** in the person's voice: the first line is a hook (LinkedIn shows two or three lines before
  "…more"), then the problem they had themselves, that others had it too, the work it took, "we tried it on
  ourselves first", what it became, and one line introducing the video ("In this video, [speaker] presents [product]"). Echo the
  video lightly; do not repeat its opening line.
- **The link in the first comment** of one's own post ("[the call to action] 👉 [link]"), pinned, because platforms
  show posts with outside links to fewer people.
- **Replies under colleagues' posts**: short, in the same tone as their post (continue their metaphor), different
  from one another so they do not look copied; thank people who credit you.
- **Mentions**: type @ and choose the person or page from the list, so they are notified. Do not invent handles on
  other platforms.
- Offer 2-4 alternatives for each line, with the recommended one first, and adapt to the user's taste quickly: they
  often want it simpler.

## 6. Final checklist

- [ ] No keys or personal paths in any delivered file or repository.
- [ ] Official logos only, exact brand colours, names and titles as the people want them.
- [ ] Subtitles checked against the voice (whisper) and as English; line breaks at phrase boundaries.
- [ ] Loudness measured (−14 LUFS, true peak ≤ −1 dBTP), no clipped samples, voice understandable under the music.
- [ ] Length within the platform limits; captions of the platform turned off.
- [ ] The call-to-action link opens the right page, in the right language.
- [ ] `docs/script.md` and `docs/spend.md` up to date.
