# Field Instrument: the Nexus design system

Nexus is a calibrated instrument for reading unknown data. The interface stays
quiet so the readout is the loudest thing on screen. One system covers the web
console (`src/nexus/web/static`), the terminal (`src/nexus/core/render.py`), and
the generated docs assets (`scripts/make_assets.py`).

**References:** Swiss International Style (flush-left grid, hierarchy from size and
weight rather than color), technical datasheets (index codes, hairline rules,
spec tables), Braun-era instrument design (restraint, one signal color), and
cryptographic history (the Polybius square).

## Mark

A 5×5 Polybius square whose filled cells spell **N**. The three diagonal cells
carry the signal color, and empty cells are drawn as hairline squares at large
sizes. In the terminal it is drawn with half blocks (`█▄  █ / █ ▀▄█ / ▀   ▀`).

## Color

| Token | Paper | Carbon | Use |
|---|---|---|---|
| `bg` | `#ECEAE3` | `#121211` | Page, behind the dot grid |
| `surface` | `#F7F6F1` | `#1A1A18` | Panels, rail, topbar |
| `well` | `#FBFAF7` | `#141413` | Inputs and output wells |
| `ink` / `ink-2` / `ink-3` | `#1A1915` `#4D4A42` `#6B675D` | `#ECE9E0` `#B9B5A9` `#8F8B80` | Text: primary, secondary, labels |
| `rule` / `rule-strong` | `#DAD6CB` `#C4BFB2` | `#2D2C28` `#3A3934` | Hairlines, registration marks |
| `control` | `#8F8A7D` | `#6E6B62` | Input borders (3:1 non-text contrast) |
| `signal` | `#E5531A` | `#F25A1A` | Marks, active state, primary action |
| `signal-ink` | `#AE3A09` | `#FF8247` | Signal-colored text (4.5:1) |
| `track` | `#F1D9CB` | `#43271A` | Unfilled meter cells |
| `critical` | `#C0312F` | `#F0605A` | Errors, always paired with a label |

All text tokens clear 4.5:1 on every surface, and marks and controls clear 3:1.
The primary button uses dark ink on signal in both themes (4.68 / 5.58).
Terminal: signal is `38;5;202` (or truecolor `#F25A1A`), labels are `245`,
tracks and rules are `240`.

## Type

IBM Plex, bundled as WOFF2 under the OFL so the console never fetches fonts.

| Role | Face | Notes |
|---|---|---|
| UI and headings | Plex Sans 400/500/600 | H1 40px/600, -0.025em |
| Data, inputs, codes | Plex Mono 400/500 | Tabular figures in columns only |
| Labels | Plex Condensed 500, 11px caps, +0.09em | The datasheet voice |

## Space and shape

4px base on an 8px rhythm (4, 8, 12, 16, 24, 32, 48, 64). The corner radius is
2px. Separation comes from hairline rules, never from drop shadows. Readout
panels carry registration marks at their corners. The page background is a 24px
dot grid, kept off panels.

## Instruments

- **Meter:** 20 cells with 2px gaps, sized `20·cell + 19·2px` so every cell lands
  on whole pixels. The fill is signal and the track is a tint of the same hue.
  The CLI mirrors it as `━` on `─`.
- **Gauge:** a hairline axis, a 3px signal run, a 10px value dot with a 2px
  surface ring, and dashed reference markers (`text`, `base64`, `random`,
  `english`). When labels would collide, one drops below the axis beside its own
  marker rather than stacking.
- **Index codes:** `01.2` = module 01, tool 2, shared by the rail, the headers,
  and the CLI.

## Motion

Motion only reports state. A 2px scan-head sweeps the readout while a request
is in flight, stale content dims, results rise 4px with a 30ms stagger, and
meter cells light up in sequence. Everything is disabled under
`prefers-reduced-motion`.

## States

Every tool has the same four states:

- **Empty:** a specimen plate (a seeded cipher-grid glyph) plus clickable samples.
- **Busy:** the scan-head and dimmed content.
- **Result:** the readout, with copy actions.
- **Error:** a critical marker, an `ERROR` label, and a mono message.
