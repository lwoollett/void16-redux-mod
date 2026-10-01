# AGENTS.md — void16-redux-mod

Guidance for AI coding agents working in this repository.

## What this repo is

A modified [VOID16](https://github.com/victorlucachi/void16) 4×4 handwired
macropad: 3D-printed two-part case (topology-optimised base + recessed plate),
nice!nano v2 controller, ZMK firmware. This repo is a **publish snapshot** —
see "Live sources" below before making changes.

## Repo layout

- `cad/` — printable STLs (top plate, bottom, fit coupon), STEP, native
  `.f3d`, and `v23_rebuild.py` (the deterministic Fusion rebuild script).
- `cad/tools/` — SIMP topology-optimisation solver (`to_solver.py`, runs on
  system python3 with numpy/scipy/skimage) and its converged-field outputs
  (`to_voids.json`, `to_inset.json`). These define the base's organic void.
- `firmware/` — snapshot of the ZMK config (self-contained). `WIRING.md`
  inside is the canonical wiring + firmware guide.
- `docs/images/` — renders.

## Live sources (where edits actually happen)

- **CAD**: the Fusion 360 document (opened as "Keyboardy thing v1"), driven
  through the fusion360-mcp-server `execute_code` API. The rebuild script
  `cad/v23_rebuild.py` regenerates the entire model deterministically —
  modify the script, never hand-edit features. After any rebuild: exports are
  refreshed into `~/Documents/void16-redux-mod/`, then copied here.
- **Firmware**: `~/repos/zmk-config-void16/` is the live repo
  (build.sh paths point there). Build with `firmware/build.sh` from the live
  repo, then sync changed files into this repo's `firmware/`.

## Ground rules for CAD changes

- **The top plate is frozen** — screw hole positions must not move.
- Case geometry constants live at the top of the rebuild script
  (`Y0/Y1 = -3.5/110.5`, `W = 84.45`, plate `PLX0..PLY1`, post lists).
  Changing a governing dimension (e.g. case length) requires sweeping the
  script for derived literals (heights must exceed the wedge plane, sketch
  extents, protection-zone offsets).
- The voronoi-lattice era is gone; the base comes from the SIMP solver. If
  the load case changes (post positions), re-run `to_solver.py` and consume
  the new JSONs — do not hand-draw struts. Keep the bay + pedestal zone as
  non-design solid in the solver so struts route around them.
- After every rebuild: the script's asserts must pass (volumes, cylinder
  histograms, sliver audits). A failed assert on a plausible build usually
  means the *expected value* is wrong — recompute before touching geometry.
- Recovery is cheap: `delete_all` + rerun the whole script. Never patch
  slivers or boolean artifacts with filler bodies — fix the script.

## Firmware notes (ZMK, nice!nano v2)

- Flat config style: `config/nice_nano.{overlay,keymap,conf}` (board-named —
  `SHIELD=` only works for registered shields).
- Board string `nice_nano//zmk`; I²C0 is hard-wired to D2/D3 (P0.17/P0.20) —
  the OLED must live there.
- ZMK-main API: `&cp` removed → `&inc_dec_kp`; physical-layout nodes require
  `transform =`; `ZEPHYR_TOOLCHAIN_VARIANT=zephyr` must be exported before
  west build (CMake 4.x bug).
- Pinout is in `firmware/WIRING.md` — matrix D4–D7 rows / D8,D9,D10,D16
  cols, encoders D1/D0 and D19/D18. Any wiring change must update the
  overlay *and* WIRING.md together.

## Conventions

- Commit CAD changes as a new `vN_rebuild.py` in `cad/` (keep prior
  versions); bump the version table in README.md.
- Keep `staged-zmk.uf2` in sync with `firmware/config/` after keymap edits.
- Renders for README go in `docs/images/` with descriptive names.
- No remote is configured; the user adds their own.
