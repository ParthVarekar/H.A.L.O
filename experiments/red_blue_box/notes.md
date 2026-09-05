# Red/Blue Box Demo

## Source

This demo is the sample experiment named in the SIH26174 problem statement (Tech Doc v1.0
§1.3): a big box contains two smaller boxes, one red and one of another colour. We chose
red and blue because they are visually distinct under typical indoor lighting and give
the YOLO detector two unambiguous colour classes to learn.

## Physical setup

- A cardboard box (~30×20×15 cm) as `big_box`.
- Two smaller rigid boxes (~8×8×8 cm): one painted matte red, one matte blue.
- A flat surface (table) for placement.
- A single fixed camera (Logitech C920 or laptop webcam) at ~1.2 m height, 60-90° HOV,
  pointed at the workspace. Camera does NOT move during a take.

## Procedure (6 steps)

1. **open_big_box** — open the lid.
2. **remove_red_box** — grasp and lift the red box out.
3. **place_red_box** — put the red box on the table.
4. **remove_blue_box** — grasp and lift the blue box out.
5. **place_blue_box** — put the blue box on the table.
6. **close_big_box** — close the lid.

## Things that must be true for the demo to work

- The two small boxes are always distinguishable by colour, even under harsh LED lighting.
- The astronaut's hand is visible to the camera whenever interacting with a box.
- The big box lid is open enough that "small box visible outside big box" is a clear signal.
- The camera frame contains the whole workspace; the table region is the fixed polygon in
  `experiment_plan.yaml` and must be recalibrated if camera resolution or placement changes.

## Recording protocol (Phase 1)

For each take:
1. 5-second setup, hands out of frame.
2. Execute the 6 steps in order at a natural pace.
3. Mix correct runs (majority) with deliberately skipped / out-of-order runs (~30%) so
   the procedure engine sees both classes.
4. Vary camera angle slightly between takes to teach the model a wider viewing range.
5. Vary lighting if possible (overhead, side, dim).

Target: ~20 takes for skeleton, ~50+ for v1 of the model.

## Swap to a different experiment

This entire demo is one YAML file. To swap in CFE-Vane-Gap, Veggie, or any other
procedure, create `experiments/<new_name>/experiment_plan.yaml` and run

```
validate-plan experiments/<new_name>/experiment_plan.yaml
```

No code changes required.
