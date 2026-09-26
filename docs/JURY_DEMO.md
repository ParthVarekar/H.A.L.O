# Jury demo: five minutes

A timed script with the lines to say. Every moment runs on one laptop without internet, on real
space-station footage the judges can pick themselves.

## Before the judges arrive

- Run `startup.bat verify` and leave the `ALL CHECKS PASSED (8/8)` output open in a terminal.
- Start the dashboard: `startup.bat`, or `startup.bat live` for the webcam.
- Disconnect from the internet. Keep a local network for the stream (a phone hotspot with mobile
  data off, a travel router, or an Ethernet cable). With no second laptop, VLC on the same laptop
  works too.
- On the second laptop, open VLC › Media › Open Network Stream › `udp://@:5000`.
- In the dashboard's **Stream to IP** card, enter the second laptop's IP and port 5000, then press
  **Start**.
- Keep two clips ready on the desktop:
  - `activities/cold_stowage_melfi/takes/slawosz_using_melfi-8821822197.mp4` (the full procedure);
  - `activities/cold_stowage_melfi/verification/step1_removed.mp4` (the same footage with step 1
    cut out).
- Turn the voice on and set the volume so the room can hear it.

## 0:00 — Wi-Fi off

Point at the network icon.

> "Everything you're about to see runs on this laptop. There's no internet and no cloud. A space
> station can't wait for a ground server, so neither do we."

## 0:30 — The judge picks the video

Offer the judge both clips and let them choose. Start with the full procedure: drag it onto the
dashboard.

> "We don't tell it which experiment this is. It recognises it."

The voice says "Recognised MELFI sample stowage. Monitoring. First: hold the sample pouch in front
of MELFI."

> "This is ESA footage from the Ignis mission: an astronaut storing a sample in MELFI, the station's
> minus-eighty-degree freezer. Eight steps, and it has to see all of them in order."

## 1:15 — It guides the crew

Point at the bar under the video: the current instruction, and **Next:** the one after it.

> "After every step it says what comes next. That's requirement two, out loud."

The voice says "Step 2 done. Next: pull tray 2 out of dewar 1." Point at the step list filling in
with times, and at the metrics: 1.00× real time, 25 frames a second, 0 alerts.

## 2:00 — Skip a step

When the first run finishes (8 of 8, "All in order"), drop in `step1_removed.mp4`.

> "Same astronaut, same footage, but we've cut out the first step. Watch."

About a second and a half in, two tones play and the voice says "Alert. Step 1 skipped." The alert
banner shows the step and the time. When the pouch appears later, it says "Alert. Step 1 done out of
order."

> "Every alert comes from a rule in the procedure file that you can read, not from a black box."

## 2:45 — The ground sees it too

Turn the second laptop around.

> "Requirement five is the video streamed to a specific IP. This is H.264 over UDP to that laptop's
> address, with the boxes drawn in, while this laptop keeps its own recording."

## 3:15 — Prove the record

Scroll to **Signed session report**.

> "The record of the session is about a kilobyte, nearly ten thousand times smaller than the video.
> That's what goes to the ground. Every event is hash-chained and signed."

In the terminal:

```bash
python -m bas_har verify-log logs\<latest>.jsonl
```

It prints `VALID`. Open the file, change one character, and run it again. It prints
`INVALID at line N`.

> "Nobody can quietly edit what happened, not even us."

## 4:00 — Teach it without training

Open `activities/melfi_zeroshot/plan.yaml` and point at one step:

```yaml
question: "Is a long cylindrical tray pulled out of the freezer, or held in the astronaut's hands?"
expect: "yes"
```

> "A new experiment can start as plain English. A vision-language model running on this laptop
> answers each question several times a second, and anything it's unsure about never ticks a box."

Optional: switch the voice to **हिं** (needs Windows' Hindi voice installed) and replay a clip.

## 4:30 — Close

Point at the terminal with `ALL CHECKS PASSED (8/8)`.

> "Everything we showed you is reproducible with one command, on footage that ships in the
> repository. We don't ask you to trust it. You can check it."

## Likely questions

- **What if the camera sees something unexpected?** A step completes only when its evidence holds
  across a short window, so one bad frame can't tick a box. Uncertain model answers are ignored.
- **How was the detector trained?** 55 labelled frames of the ISS footage in our Training Studio,
  with 11 held back for testing. Held-out mAP50 is 0.79. The detector is in the repository.
- **Why not a single end-to-end network?** Flight procedures need explanations. Our engine is
  deterministic and every alert names the rule it broke. Perception feeds it evidence.
- **Does it need the internet?** No. Every model runs locally, and `python -m bas_har verify` works
  with the network unplugged.
- **What about 3D body tracking?** It isn't in this release. We recognise steps from what happens
  to the equipment, which is what a procedure is checked against.
