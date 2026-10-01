# void16-redux-mod — Wiring & Firmware Guide

Complete build documentation: handwiring, power, enclosure hardware, firmware, flashing.

---

## 1. Bill of electrical parts

| Part | Spec | Qty | Notes |
|---|---|---|---|
| Controller | nice!nano v2 (nRF52840) | 1 | mounts on the pedestal, guides retain it |
| Switch PCBs | per-switch, 1N4148 diode each | 16 | diode stripe (cathode) → ROW wire |
| Encoders | EC11, plate-mount | 2 | flanking the screen; push legs unused |
| OLED | SSD1306 I²C, 0.91"/0.96" | 1 | 128×32 default firmware; 128×64 = 2-line config change |
| Battery | 402030 LiPo 200mAh + protection PCM | 1 | drops in the battery bay from above |
| Power switch | SPDT slide, side-actuator (MSK-12C02 family) | 1 | left-wall slot |
| Reset button | 6×6 horizontal tactile w/ bracket, 5mm actuator | 1 | behind pinhole, right wall (v22+) |
| Wire | 24–26 AWG solid/stranded | ~2m | matrix buses 24AWG, signals 26AWG |

---

## 2. Matrix wiring (col2row)

```
        (viewed from above, USB/encoders at the top, typing position)

     ENC-L                            ENC-R
    A=D1 B=D0                        A=D19 B=D18
     │  │          COL0   COL1   COL2   COL3
     │  │           D8     D9     D10    D16
     │  │            │      │      │      │
     │  │  ROW0 D4 ──┼──7────┼──8───┼──9───┼──÷──┐
     │  │            │      │      │      │      │
     │  │  ROW1 D5 ──┼──4────┼──5───┼──6───┼──×──┐│
     │  │            │      │      │      │     ││
     │  │  ROW2 D6 ──┼──1────┼──2───┼──3───┼───−┐││
     │  │            │      │      │      │    │││
     │  │  ROW3 D7 ──┼──0────┼──.───┼─ENT──┼─FN┐│││
     │  │                                                  ROW bus (4 wires)
     └──┴── GND (ENC commons ×2)                          COL bus (4 wires)
   (numbers = numpad legend of default layer)
```

- Each switch: one leg → its ROW bus wire; other leg (through PCB diode, **stripe→ROW**) → its COL bus wire.
- Run ROW/COL buses through the 5mm gaps between the switch PCB columns, down to the MCU pedestal.
- Dead-key after wiring = one diode backwards (stripe must face the row wire).

## 3. nice!nano v2 pin map

| Function | pro_micro N | nRF GPIO | silk | | Function | pro_micro N | nRF GPIO | silk |
|---|---|---|---|---|---|---|---|---|
| ROW0 | 4 | P0.22 | "4" | | COL2 | 10 | P0.09 | "10" |
| ROW1 | 5 | P0.24 | "5" | | COL3 | 16 | P0.10 | "16" |
| ROW2 | 6 | P1.00 | "6" | | ENC-L A | 1 | P0.06 | "1" |
| ROW3 | 7 | P0.11 | "7" | | ENC-L B | 0 | P0.08 | "0" |
| COL0 | 8 | P1.04 | "8" | | ENC-R A | 19 | P0.02 | "19" |
| COL1 | 9 | P1.06 | "9" | | ENC-R B | 18 | P1.15 | "18" |

- **OLED: SDA=D2 (P0.17), SCL=D3 (P0.20)** — hardware i2c0, the ONLY working pair. VCC→3V3, GND→GND.
- **EC11 encoders**: both COMMON pins → GND. A/B → pins above. Push-switch legs: unused.
- Battery + switch: see power section. All grounds star at the nice!nano GND pins.

## 4. Power wiring

```
 402030 LiPo                          nice!nano v2 (underside)
 ┌──────────┐                         ┌─────────────┐
 │ + (red) ─┼──► pin 2 ── pin 1 ──►──┼ BATT/B2B +  │   slide switch
 │          │        (MSK-12C02)      │             │   in left-wall slot
 │ − (blk) ─┼──────────────────────►──┼ B2B  GND    │
 └──────────┘                         └─────────────┘
```

- SPDT slide: use centre pin + one outer. In series with battery RED only.
- Route: red lead over the bay lip at z≈6, across the cavity to the left-wall switch
  (~45mm), back to BATT. Hot-glue to the web top so it can't sag onto PCBs.
- **Charges only when switch ON** (charger sees battery through it) — leave ON when on USB.
- Reversing battery polarity on B2B pads kills the nice!nano. Check twice, power once.
- Charge current 100mA → ~2h for 200mAh. Over-discharge protection lives in the battery PCM.

## 5. Reset button (v22 case)

- 6×6×5h horizontal tactile with bracket, glued to the inside of the wall behind the
  **Ø2.5 pinhole**, actuator facing the hole.
- Wire: one pin → RST, other → GND on the nice!nano.
- Poke a paperclip through the pinhole to press. **Double-press = bootloader (NICEBOOT
  drive)** — same button, two presses, no disassembly.

## 6. Firmware

Repo: `~/repos/zmk-config-void16/` (flat config, board `nice_nano//zmk`).

```
config/nice_nano.overlay   kscan + encoders + OLED + physical layout
config/nice_nano.keymap    layers (see below)
config/nice_nano.conf      encoder + display Kconfigs
build.sh                   full build → staged-zmk.uf2
```

**Keymap**

| Layer | Grid | ENC-L | ENC-R |
|---|---|---|---|
| 0 (Num) | 7 8 9 ÷ / 4 5 6 × / 1 2 3 − / 0 . ⏎ FN | volume | track |
| 1 (FN) | F13–F16 / F9–F12 / F5–F8 / F1–F4 | pgup/pgdn | home/end |

**Build & flash**
```
./build.sh
# double-tap RST (or the reset pinhole ×2) → NICEBOOT drive
cp staged-zmk.uf2 /Volumes/NICEBOOT/ && diskutil eject NICEBOOT
```

**OLED panel variant**: 128×64 panels → in `config/nice_nano.overlay` set
`height = <64>` and `multiplex-ratio = <63>`, rebuild.

**Adding soft-off instead of the slide switch**: bind `&soft_off` on any key
(deep sleep ≈ 20µA) — ask and it gets added + rebuilt.
