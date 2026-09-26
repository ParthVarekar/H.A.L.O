# Verification

Three commands let anyone reproduce the headline result on their own machine and check the evidence
it produces. They need nothing but this repository. The ISS footage, its labels and the trained
detector all ship with it, and the commands never touch the network.

## 1. Reproduce the reference run

```bash
python -m bas_har verify
```

This runs the committed ESA Ignis take (`activities/cold_stowage_melfi/takes/`, 67 s) through the
same session runner the dashboard uses, on every frame. It then runs the same footage with its first
step cut out (`activities/cold_stowage_melfi/verification/step1_removed.mp4`). Expected output, on an
RTX 5050 laptop in about a minute:

```text
  PASS  Experiment plans validate      6 of 6
  PASS  Reference take runs            cuda:0 · 37.3 s
  PASS  Every step recognised          8 of 8
  PASS  Steps in the planned order     no skips, none late
  PASS  No false alerts                0 alerts
  PASS  Signed event log verifies      42 lines · Ed25519 · key 443ab90de63c4fec
  PASS  Downlink report seals the log  1,002 bytes · 9,701x smaller than the video
  PASS  Removed step is caught         skip alert 1.48 s into the clip with step 1 cut out

  ALL CHECKS PASSED (8/8)
```

The key id is different on every machine, because each machine creates its own signing key on first
use and keeps it in `keys/`. On a computer without an NVIDIA GPU the run uses the CPU and takes
longer.

## 2. Check a signed event log

```bash
python -m bas_har verify-log logs/web_cold_stowage_melfi_<stamp>.jsonl
```

```text
VALID  42 lines, 41 events, signed by station key 443ab90de63c4fec
       final hash 2cfa34002a1b8ccaf50e8f12eb5e3d0bc139be9da0cf144ca8a99bc0770c760c
```

Change one character anywhere in the file and run it again:

```text
INVALID at line 14: content changed: hash does not match
```

Each line holds the SHA-256 hash of the line before it, and every hash is signed with the station's
Ed25519 key. Editing, deleting or reordering a line breaks the chain. Rebuilding the chain needs the
private key.

## 3. Check the downlink report

```bash
python -m bas_har verify-downlink logs/web_cold_stowage_melfi_<stamp>.downlink.json --log logs/web_cold_stowage_melfi_<stamp>.jsonl
```

```text
VALID  1,002 bytes, signed by station key 443ab90de63c4fec and seals the given log
```

The downlink report is the session in about a kilobyte: every step with its time, every alert, the
event count and the log's final hash, all signed. It is what a station would send to the ground
instead of video. Because it seals the final hash and the count, a log with lines cut from the end
fails this check even though its own chain is intact.

## Component results

| Component | Check | Result |
|---|---|---|
| Procedure recognition | ISS MELFI take, every frame | 8 of 8 steps in order, 0 alerts |
| Skip detection | Same footage with step 1 cut out | Skip alert at 1.48 s, out-of-order alert at 3.0 s when the step appears late |
| Real-time dashboard | Same take played at its own speed | 1.00× real time at 25 fps |
| Trained detector | YOLO11n, 44 training / 11 held-out frames, no horizontal flip | Held-out mAP50 0.79 |
| Vision-language questions | Qwen3-VL-2B, 9 questions in one pass | 0.61 s per pass, off the video path |
| Signed log | Edit, delete, reorder, truncate, forged signature, other key | All detected (`tests/test_signed_log.py`) |
| Downlink report | MELFI session | 1,002 bytes, 9,701× smaller than the 9.7 MB video, verified |
| Stream to IP | MPEG-TS over UDP to a second process | 508 H.264 frames decoded (NVENC encoder) |
| Next-step voice | MELFI session | "Step 2 done. Next: pull tray 2 out of dewar 1." for every step |
| Test suite | `pytest` | 276 passed |

The full record, including the rows that did not pass during development, is in
[validation_matrix.md](validation_matrix.md).
