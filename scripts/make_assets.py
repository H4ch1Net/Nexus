"""Regenerate every README / brand asset from the live product.

Renders the brand banners and social card from HTML (using the bundled fonts),
screenshots the web console in both themes, and captures real CLI output as
images. Nothing is mocked: screenshots come from a running `nexus serve` and
CLI images from actual command output.

    pip install -e ".[docs]"
    python scripts/make_assets.py              # all assets
    CHROMIUM_PATH=/path/to/chrome python scripts/make_assets.py

Requires Playwright with a Chromium build (set CHROMIUM_PATH to use a specific
binary). Output goes to assets/brand and assets/screens.
"""
from __future__ import annotations

import html
import io
import os
import re
import subprocess
import sys
import threading
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nexus import __version__  # noqa: E402
from nexus.web.server import serve  # noqa: E402

# Set in main() to the running server, which serves the bundled fonts at /fonts.
FONTS = ""
BRAND = ROOT / "assets/brand"
SCREENS = ROOT / "assets/screens"

THEMES = {
    "paper": dict(bg="#ECEAE3", surface="#F7F6F1", well="#FBFAF7", ink="#1A1915", ink2="#4D4A42", ink3="#6B675D",
                  rule="#DAD6CB", rule_strong="#C4BFB2", dot="#D3CFC4", signal="#E5531A", signal_ink="#AE3A09",
                  track="#F1D9CB", faint="#BDB8AB", critical="#C0312F"),
    "carbon": dict(bg="#121211", surface="#1A1A18", well="#141413", ink="#ECE9E0", ink2="#B9B5A9", ink3="#8F8B80",
                   rule="#2D2C28", rule_strong="#3A3934", dot="#262522", signal="#F25A1A", signal_ink="#FF8247",
                   track="#43271A", faint="#4A4842", critical="#F0605A"),
}

N_GRID = ["X...X", "XX..X", "X.X.X", "X..XX", "X...X"]


# ---------------------------------------------------------------------------
# Shared HTML pieces
# ---------------------------------------------------------------------------
def font_css() -> str:
    assert FONTS, "font base URL not set"
    faces = [("Plex Sans", "ibm-plex-sans", (400, 500, 600)),
             ("Plex Mono", "ibm-plex-mono", (400, 500)),
             ("Plex Condensed", "ibm-plex-sans-condensed", (500, 600))]
    return "".join(
        f'@font-face{{font-family:"{fam}";src:url("{FONTS}/{stem}-latin-{w}-normal.woff2");font-weight:{w}}}'
        for fam, stem, weights in faces for w in weights)


def mark_svg(t: dict, cell: int = 26, gap: int = 8) -> str:
    rects = []
    for r, row in enumerate(N_GRID):
        for c, ch in enumerate(row):
            x, y = c * (cell + gap), r * (cell + gap)
            if ch == "X":
                fill = t["signal"] if (r == c and 0 < r < 4) else t["ink"]
                rects.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{fill}"/>')
            else:
                rects.append(f'<rect x="{x + .75}" y="{y + .75}" width="{cell - 1.5}" height="{cell - 1.5}" rx="2" '
                             f'fill="none" stroke="{t["rule_strong"]}" stroke-width="1.5"/>')
    size = 5 * cell + 4 * gap
    return f'<svg viewBox="0 0 {size} {size}" width="{size}" height="{size}">{"".join(rects)}</svg>'


def base_css(t: dict) -> str:
    return f"""{font_css()}
    *{{box-sizing:border-box}} html,body{{margin:0}}
    body{{background:{t['bg']};color:{t['ink']};font-family:"Plex Sans";-webkit-font-smoothing:antialiased}}
    .dots{{background-image:radial-gradient({t['dot']} 1.2px,transparent 1.4px);background-size:24px 24px;background-position:-12px -12px}}
    .label{{font-family:"Plex Condensed";font-weight:500;text-transform:uppercase;letter-spacing:.09em;color:{t['ink3']}}}
    .code{{font-family:"Plex Mono";color:{t['signal_ink']}}}
    .reg{{position:relative}}
    .reg::before{{content:"";position:absolute;inset:-9px;pointer-events:none;
      background:linear-gradient({t['rule_strong']},{t['rule_strong']}) left top/10px 1px no-repeat,
      linear-gradient({t['rule_strong']},{t['rule_strong']}) left top/1px 10px no-repeat,
      linear-gradient({t['rule_strong']},{t['rule_strong']}) right top/10px 1px no-repeat,
      linear-gradient({t['rule_strong']},{t['rule_strong']}) right top/1px 10px no-repeat,
      linear-gradient({t['rule_strong']},{t['rule_strong']}) left bottom/10px 1px no-repeat,
      linear-gradient({t['rule_strong']},{t['rule_strong']}) left bottom/1px 10px no-repeat,
      linear-gradient({t['rule_strong']},{t['rule_strong']}) right bottom/10px 1px no-repeat,
      linear-gradient({t['rule_strong']},{t['rule_strong']}) right bottom/1px 10px no-repeat}}"""


def readout_vignette(t: dict, scale: float = 1.0) -> str:
    """A miniature readout: the product's signature moment, as an illustration."""
    segs = "".join(f'<i style="background:{t["signal"] if i < 20 else t["track"]}"></i>' for i in range(20))
    alt = "".join(f'<i style="background:{t["signal"] if i < 16 else t["track"]}"></i>' for i in range(20))
    return f"""
    <div class="vig reg" style="zoom:{scale}">
      <div class="vh"><span class="label">Readout</span><span class="vm">2 recipes · 9 ms</span></div>
      <div class="vr">
        <div class="vt"><span class="vn" style="color:{t['signal_ink']}">01</span>
          <span class="step lead">base64</span><span class="arr">→</span><span class="step lead">base64</span>
          <span class="badge">Best</span><span class="segs">{segs}</span><span class="pct">100%</span></div>
        <div class="out">flag{{nexus_field_instrument}}</div>
      </div>
      <div class="vr alt"><span class="vn">02</span><span class="step">rot13</span>
        <span class="prev">Jz14nSbmqUInJTtkLmR5nzVlAKcv…</span><span class="segs sm">{alt}</span><span class="pct">81%</span></div>
    </div>"""


def vignette_css(t: dict) -> str:
    return f"""
    .vig{{width:470px;background:{t['surface']};border:1px solid {t['rule']};border-radius:2px}}
    .vh{{display:flex;justify-content:space-between;align-items:center;height:38px;padding:0 16px;border-bottom:1px solid {t['rule']}}}
    .vh .label{{font-size:11px;color:{t['ink2']}}} .vm{{font-family:"Plex Mono";font-size:11.5px;color:{t['ink3']}}}
    .vr{{padding:14px 16px;border-bottom:1px solid {t['rule']}}} .vr:last-child{{border-bottom:0}}
    .vt{{display:flex;align-items:center;gap:7px;margin-bottom:11px}}
    .vn{{font-family:"Plex Mono";font-size:11.5px;color:{t['ink3']};width:20px}}
    .step{{font-family:"Plex Mono";font-weight:500;font-size:11.5px;padding:4px 6px;border:1px solid {t['rule_strong']};border-radius:2px;background:{t['well']};color:{t['ink2']}}}
    .step.lead{{border-color:{t['signal']};color:{t['ink']}}}
    .arr{{font-family:"Plex Mono";font-size:12px;color:{t['ink3']}}}
    .badge{{font-family:"Plex Condensed";font-weight:600;font-size:10px;letter-spacing:.1em;text-transform:uppercase;background:{t['signal']};color:{'#1A1915' if t is THEMES['paper'] else '#121211'};padding:3px 5px 2px;border-radius:1px}}
    .segs{{display:grid;grid-template-columns:repeat(20,1fr);gap:2px;width:98px;height:9px;margin-left:auto}}
    .segs.sm{{width:78px}} .segs i{{border-radius:1px}}
    .pct{{font-family:"Plex Mono";font-size:11.5px;width:34px;text-align:right}}
    .out{{font-family:"Plex Mono";font-size:15px;padding:11px 13px;background:{t['well']};border:1px solid {t['rule']};border-radius:2px}}
    .alt{{display:flex;align-items:center;gap:8px;padding:10px 16px}}
    .prev{{font-family:"Plex Mono";font-size:11.5px;color:{t['ink3']};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;flex:1}}"""


def brand_page(t: dict, width: int, height: int, big: bool) -> str:
    mods = "".join(f'<span><b class="code">{c}</b>{n}</span>' for c, n in
                   (("01", "Cryptography"), ("02", "Enumeration"), ("03", "OSINT"), ("04", "Logs")))
    cell, word, tag = (30, 112, 25) if big else (22, 84, 20)
    return f"""<!doctype html><html><head><style>{base_css(t)}{vignette_css(t)}
    .frame{{width:{width}px;height:{height}px;position:relative;overflow:hidden;display:flex;align-items:center;
      padding:0 {72 if big else 64}px;gap:{56 if big else 44}px;border:1px solid {t['rule']}}}
    .left{{display:flex;flex-direction:column;gap:{22 if big else 16}px;min-width:0}}
    .lock{{display:flex;align-items:center;gap:{34 if big else 26}px}}
    .word{{font-family:"Plex Mono";font-weight:500;font-size:{word}px;letter-spacing:-.03em;line-height:.9}}
    .eyebrow{{display:flex;align-items:center;gap:10px;font-size:{13 if big else 12}px}}
    .eyebrow .bar{{width:28px;height:1px;background:{t['rule_strong']}}}
    .tag{{font-size:{tag}px;color:{t['ink2']};max-width:560px;line-height:1.35;letter-spacing:-.005em}}
    .mods{{display:flex;gap:22px;font-size:{12.5 if big else 11.5}px}} .mods span{{display:flex;gap:7px}}
    .mods b{{font-weight:400}}
    .right{{margin-left:auto;align-self:center}}
    .corner{{position:absolute;right:{72 if big else 64}px;bottom:{26 if big else 18}px;font-size:11px}}
    </style></head><body>
    <div class="frame dots">
      <div class="left">
        <div class="eyebrow label"><span class="code">v{__version__}</span><span class="bar"></span>Field instrument for unknown data</div>
        <div class="lock">{mark_svg(t, cell=cell, gap=int(cell * .3))}<div class="word">nexus</div></div>
        <div class="tag">Decode, hash, identify, extract.<br>Entirely offline, on your machine.</div>
        <div class="mods label">{mods}</div>
      </div>
      <div class="right">{readout_vignette(t, 1.12 if big else .86)}</div>
    </div></body></html>"""


# ---------------------------------------------------------------------------
# ANSI -> HTML for CLI captures
# ---------------------------------------------------------------------------
_ANSI = re.compile(r"\x1b\[([0-9;]*)m")


def ansi_to_html(text: str, t: dict) -> str:
    palette = {"202": t["signal"], "245": t["ink3"], "240": t["faint"], "203": t["critical"]}
    out, style, pos = [], {}, 0

    def emit(chunk: str):
        if not chunk:
            return
        css = []
        if "fg" in style:
            css.append(f"color:{style['fg']}")
        if style.get("b"):
            css.append("font-weight:600")
        out.append(f'<span style="{";".join(css)}">{html.escape(chunk)}</span>' if css else html.escape(chunk))

    for m in _ANSI.finditer(text):
        emit(text[pos:m.start()])
        pos = m.end()
        codes = (m.group(1) or "0").split(";")
        i = 0
        while i < len(codes):
            code = codes[i]
            if code in ("0", ""):
                style = {}
            elif code == "1":
                style["b"] = True
            elif code == "38" and i + 2 < len(codes) and codes[i + 1] == "5":
                style["fg"] = palette.get(codes[i + 2], t["ink"]); i += 2
            elif code == "38" and i + 4 < len(codes) and codes[i + 1] == "2":
                style["fg"] = t["signal"]; i += 4
            i += 1
    emit(text[pos:])
    return "".join(out)


def terminal_page(t: dict, command: str, body_html: str) -> str:
    return f"""<!doctype html><html><head><style>{base_css(t)}
    .stage{{padding:36px;display:inline-block}}
    .term{{background:{t['surface']};border:1px solid {t['rule']};border-radius:2px;width:860px}}
    .bar{{display:flex;align-items:center;gap:10px;height:38px;padding:0 18px;border-bottom:1px solid {t['rule']};font-size:11px}}
    .bar .sq{{width:7px;height:7px;background:{t['signal']};border-radius:1px}}
    .bar .sp{{flex:1}}
    pre{{margin:0;padding:20px 22px 24px;font-family:"Plex Mono","DejaVu Sans Mono","Liberation Mono",monospace;font-size:13.5px;line-height:1.55;color:{t['ink']}}}
    .ps{{color:{t['signal']}}} .cmd{{color:{t['ink']}}}
    </style></head><body><div class="stage dots"><div class="term reg">
      <div class="bar label"><span class="sq"></span>Terminal<span class="sp"></span><span class="code">nexus {__version__}</span></div>
      <pre><span class="ps">$</span> <span class="cmd">{html.escape(command)}</span>

{body_html}</pre></div></div></body></html>"""


def run_cli(args: list[str]) -> str:
    env = dict(os.environ, NEXUS_FORCE_COLOR="1", COLORTERM="", PYTHONPATH=str(ROOT / "src"))
    env.pop("NO_COLOR", None)
    proc = subprocess.run([sys.executable, "-m", "nexus.cli", *args], capture_output=True, text=True, env=env)
    return proc.stdout.rstrip("\n")


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------
def save_png(png: bytes, path: Path) -> None:
    """Quantize flat UI captures to a palette PNG to keep the repository small."""
    img = Image.open(io.BytesIO(png)).convert("RGB")
    img.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(path, optimize=True)
    print(f"  {path.relative_to(ROOT)}  {path.stat().st_size // 1024} KB")


def main() -> None:
    BRAND.mkdir(parents=True, exist_ok=True)
    SCREENS.mkdir(parents=True, exist_ok=True)
    try:
        httpd = serve("127.0.0.1", 8765)  # the documented default, so captures match the README
    except OSError:
        httpd = serve("127.0.0.1", 0)
    base = f"http://127.0.0.1:{httpd.server_address[1]}/"
    global FONTS
    FONTS = base + "fonts"
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    exe = os.environ.get("CHROMIUM_PATH")
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=exe, args=["--no-sandbox"]) if exe else p.chromium.launch()

        def page(w, h, scheme="light", dpr=2):
            ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=dpr, color_scheme=scheme)
            pg = ctx.new_page()
            # Adopt the server origin (same-origin fonts) before set_content.
            pg.route(base + "__blank", lambda r: r.fulfill(body="<!doctype html><html></html>", content_type="text/html"))
            pg.goto(base + "__blank")
            return pg

        print("brand")
        for name, t in THEMES.items():
            pg = page(1280, 400)
            pg.set_content(brand_page(t, 1280, 400, big=False)); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(200)
            save_png(pg.locator(".frame").screenshot(), BRAND / f"banner-{name}.png")
        pg = page(1280, 640)
        pg.set_content(brand_page(THEMES["paper"], 1280, 640, big=True)); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(200)
        save_png(pg.locator(".frame").screenshot(), BRAND / "social-preview.png")

        print("cli")
        vig = "GLB UFNPVML EIXX LUI FHLRVZYHG XTCUR EKX LUIK QJBXB XGJR QBW XIV"
        nested = "Wm14aFozdHVaWGgxYzE5amIyNXpiMnhsZlE9PQ=="
        captures = {
            "cli-detect": (f'nexus crypt detect -i "{vig[:22]}…" -f detailed --top 5',
                           ["crypt", "detect", "-i", vig, "-f", "detailed", "--top", "5"]),
            "cli-decode": (f"nexus crypt decode -i {nested}", ["crypt", "decode", "-i", nested]),
        }
        for stem, (shown, args) in captures.items():
            raw = run_cli(args)
            for name, t in THEMES.items():
                pg = page(1000, 900, "dark" if name == "carbon" else "light")
                pg.set_content(terminal_page(t, shown, ansi_to_html(raw, t))); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(200)
                save_png(pg.locator(".stage").screenshot(), SCREENS / f"{stem}-{name}.png")

        print("web")
        shots = [("decode", 0, 1080), ("detect", 1, 1240), ("iocs", 0, 1200)]
        for tool, sample, height in shots:
            for name in THEMES:
                pg = page(1360, height, "dark" if name == "carbon" else "light")
                pg.goto(f"{base}#{tool}"); pg.wait_for_timeout(400)
                pg.locator(".sample").nth(sample).click(); pg.wait_for_timeout(900)
                pg.evaluate("document.activeElement && document.activeElement.blur()")
                pg.mouse.move(0, 0); pg.wait_for_timeout(150)
                save_png(pg.screenshot(), SCREENS / f"web-{tool}-{name}.png")

        # Mobile pair composited onto the brand background.
        phones = []
        for name, tool in (("paper", "detect"), ("carbon", "decode")):
            pg = page(390, 844, "dark" if name == "carbon" else "light", dpr=2)
            pg.goto(f"{base}#{tool}"); pg.wait_for_timeout(400)
            pg.locator(".sample").nth(0).click(); pg.wait_for_timeout(900)
            pg.evaluate("document.activeElement && document.activeElement.blur(); window.scrollTo(0, 0)")
            pg.wait_for_timeout(150)
            phones.append(Image.open(io.BytesIO(pg.screenshot())).convert("RGB"))
        pad, gap = 96, 72
        w, h = phones[0].size
        canvas = Image.new("RGB", (pad * 2 + w * 2 + gap, pad * 2 + h), THEMES["paper"]["bg"])
        for i, im in enumerate(phones):
            x, y = pad + i * (w + gap), pad
            border = Image.new("RGB", (w + 4, h + 4), THEMES["paper"]["rule_strong"])
            canvas.paste(border, (x - 2, y - 2)); canvas.paste(im, (x, y))
        buf = io.BytesIO(); canvas.save(buf, "PNG")
        save_png(buf.getvalue(), SCREENS / "web-mobile.png")

        browser.close()
    httpd.shutdown()


if __name__ == "__main__":
    main()
