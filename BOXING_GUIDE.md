# Helping Box Videos — a Guide for Friends

Thanks for helping out! This page explains, in plain terms, what "boxing a video" means for this
project and walks you through doing it. No coding knowledge needed.

## What is this project?

It's a system that watches a video of someone doing a hands-on procedure (like an astronaut
running a science experiment on the ISS) and automatically checks whether each step was done, in
the right order, at the right time — with a voice announcing progress and alerts.

For it to recognise objects in a video (a freezer door, a sample pouch, a tray, and so on), it
needs examples of what those objects look like. That's what "boxing" is: drawing a rectangle
around an object in a paused video frame and telling the system what it is. Do this on enough
frames, and the system learns to spot that object on its own in any frame of the video.

## What "boxing" actually looks like

You'll open a page in your browser, pick a moment in the video, and drag a rectangle around each
object you can see — a freezer, a hand, a sample pouch, whatever the project needs. If an object
has a "state" (like a door that can be open or closed), you'll also pick which state it's in from
a dropdown. Save, move to the next frame, repeat. That's it. It's closer to a simple, repetitive
labelling task than programming.

You do **not** need to write any code, install anything unusual, or understand the AI behind it.

## One-time setup

You'll need:

- **Windows**, with **Python 3.11** or 3.12 installed (not 3.13+ — the project pins an older
  version because of a library it depends on)
- **Node.js** (for building the web page you'll use)
- A copy of this repository

From PowerShell, in the folder where you want the project:

```powershell
git clone https://github.com/ParthVarekar/HAR_for_BAS.git
cd HAR_for_BAS
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[perception,streaming,voice,studio,dev]"
```

This downloads the Python packages the project needs. It can take a few minutes the first time.

## Starting the labelling tool

From the project folder:

```powershell
startup_training_studio.bat
```

This builds and opens a page in your browser at `http://127.0.0.1:5767/?workspace=studio`. It's
a page running entirely on your own computer — nothing is uploaded anywhere.

When you're done for the session, close it with:

```powershell
close_training_studio.bat
```

(This only closes what `startup_training_studio.bat` started, so it won't touch anything else
running on your computer.)

## Walking through the page

The page is organised top to bottom as numbered steps. As a labeller, you mostly care about one
of them — **"STEP 05 — Assist frame annotation"** — but here's what the others are, so nothing
looks mysterious:

- **Local packages** (left side): a list of activities (experiments/procedures) already in the
  project. Click one to work on it — ask whoever asked you to help which one they want boxed.
- **STEP 01 — Approved procedure**: the steps of the procedure and the list of objects it cares
  about. You don't need to edit this; just glance at the object list so you know what names to use.
- **STEP 02 — Training videos**: the video(s) already uploaded for this activity.
- **STEP 03 — Ground truth timeline**: roughly when each step happens in the video. Also not
  something you'll usually touch.
- **STEP 04 — Prepare and train**: this is where the AI model actually gets trained, later, after
  boxing is done. Leave this alone unless you've been asked to run it.
- **STEP 05 — Assist frame annotation**: **this is where you'll spend your time.** See below.
- **STEP 06 — Quality gate and evaluation**: a report on whether there's enough labelled data.
  Also not your job — check it if you're curious.

## STEP 05 — the actual boxing

1. **Pick the take** (video) from the dropdown, if more than one exists.
2. **"Sample every frames"** controls how many frames you get to choose from — a smaller number
   gives you more frames spaced closer together. It resets to 30 each time you reload the page.
3. **Pick a frame** from the frame list.
4. **Pick a label** from the dropdown — this is the name of the object you're about to box (e.g.
   `dewar_hatch`). If that object has a **state**, a second dropdown appears — pick which state
   it's in right now (e.g. `open` or `closed`). A box won't save without picking a state if its
   class needs one.
5. **Drag a rectangle** around the object, as tightly as you reasonably can.
6. **Save it**:
   - Press `Enter`, or click **"Save label"**, to save and stay on the same frame (so you can box
     more objects in it).
   - Press `Shift+Enter`, or click **"Save & next frame"**, to save and move on.
7. Repeat for every object visible in that frame, including objects that are *inside* other
   objects — for example, a sample pouch sitting inside an open compartment. You can drag a new
   box starting from inside an existing one; it won't interfere.
8. When you move to a new frame where nothing has changed much from the last one, you can click
   **"Copy boxes from previous frame"** to bring over the previous frame's boxes, then just
   redraw or delete the ones that actually moved, instead of starting from scratch.
9. Every box you've already saved on the current frame shows up in a small list below the image,
   where you can change its state, redraw it, or delete it if you made a mistake.

## The three rules that actually matter

1. **Only box what you can actually see.** If an object isn't visible in this frame, don't guess
   where it might be — just skip it for this frame.
2. **Box tightly.** The rectangle should hug the object, not include a lot of empty space around
   it.
3. **Pick the right state, don't guess it.** If you can't tell whether something is open or
   closed in a given frame, it's fine to skip boxing that object on that frame rather than
   guessing.

Nothing you do here can break anything — every box is saved the moment you save it, and mistakes
can always be redrawn or deleted from the box list.

## Quick reference: what's boxed already

- `activities/cold_stowage_melfi` — 775 boxes on 55 frames, already boxed and used to train a
  model. If you're asked to add *more* frames to it (for better accuracy, or for a second
  recording of the same experiment), just carry on the same way — pick unboxed frames and box
  them the same way described above.

For the exact list of object names and what they mean for the current activity, see
`dataset_progress.md` in the project root — it has an up-to-date table for whichever experiment
is currently being worked on.

## If something looks wrong

- **The video is missing or the page won't load an activity**: close and restart
  `startup_training_studio.bat`, then reload the browser page.
- **The dropdown for an object's state is greyed out ("No states")**: that object doesn't have
  states — just pick the label and box it, no state needed.
- **You're not sure which object name to use**: check STEP 01's object list on the page, or ask
  whoever's coordinating the boxing.

If you get stuck on anything not covered here, just ask — this guide covers the common case, not
every edge case.

## Is boxing always needed?

Not always. The project can also watch an experiment that has only been *described* in plain
English — you write what each object looks like ("a freezer rack with round doors") and what
question should be true at each step ("is one of the round freezer doors open?"), and no boxing or
training happens at all. `activities/melfi_zeroshot` is set up that way.

Describing is much faster to set up and works on video the project has never seen before, but it
can only check what is plainly visible in the picture. On a test video it followed a whole
freezer cycle (tray out, sample taken, tray back, door closed), but it can't see a small lid
hidden under a glove, or which way a latch is turned. Those are exactly the things worth boxing.
So: describe first, see which steps it gets, and box only the objects it can't see.
