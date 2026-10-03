"use strict";

/* ==========================================================================
   Nexus console. Vanilla JS, no dependencies, no network beyond loopback.
   ========================================================================== */

// ---------------------------------------------------------------------------
// DOM helpers (user data always goes in as text nodes, never as HTML)
// ---------------------------------------------------------------------------
const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "class") node.className = v;
    else if (k === "style") node.style.cssText = v;
    else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) {
    if (kid == null || kid === false) continue;
    node.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  }
  return node;
};
const fromMarkup = (markup) => {
  const t = document.createElement("template");
  t.innerHTML = markup.trim();
  return t.content.firstElementChild;
};
const pct = (x) => `${Math.round((x || 0) * 100)}%`;
const pad2 = (n) => String(n).padStart(2, "0");
const pretty = (s) => String(s).replace(/_/g, " ");
const isMac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);

// ---------------------------------------------------------------------------
// Iconography: 16px grid, 1.5px stroke, square caps. Static markup only.
// ---------------------------------------------------------------------------
const ICON_PATHS = {
  detect: '<circle cx="8" cy="8" r="4.25"/><path d="M8 1v3.25M8 11.75V15M1 8h3.25M11.75 8H15"/><rect x="7.25" y="7.25" width="1.5" height="1.5" fill="currentColor" stroke="none"/>',
  decode: '<circle cx="4.75" cy="8" r="3"/><path d="M7.75 8H15M12.5 8v2.75M15 8v2"/>',
  hash: '<path d="M6.25 1.75 4.75 14.25M11.25 1.75 9.75 14.25M2.25 5.5h12M1.75 10.5h12"/>',
  hashid: '<path d="M1.75 1.75h6.5L14.25 8l-6 6.25-6.5-6.5z"/><rect x="4.5" y="4.5" width="1.75" height="1.75" fill="currentColor" stroke="none"/>',
  codeid: '<path d="M5 4.25 1.5 8 5 11.75M11 4.25 14.5 8 11 11.75M9.5 2.5l-3 11"/>',
  ports: '<path d="M1.75 2.75h12.5v8.5h-3v2.5h-6.5v-2.5h-3z"/><path d="M5.5 5.75v2M8 5.75v2M10.5 5.75v2"/>',
  iocs: '<circle cx="8" cy="8" r="6.25"/><circle cx="8" cy="8" r="3"/><path d="M8 8 12.4 3.6"/>',
  defang: '<path d="M7 4.6 8.6 3a2.8 2.8 0 0 1 4 4L11 8.6M9 11.4 7.4 13a2.8 2.8 0 0 1-4-4L5 7.4"/><path d="M1.5 4.5h2M4.5 1.5v2M14.5 11.5h-2M11.5 14.5v-2"/>',
  copy: '<rect x="5.25" y="5.25" width="9" height="9"/><path d="M10.75 5.25v-3.5h-9v9h3.5"/>',
  check: '<path d="M2.75 8.5 6.25 12l7-8"/>',
};
const icon = (name) => fromMarkup(
  `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="square" stroke-linejoin="miter" aria-hidden="true">${ICON_PATHS[name]}</svg>`);
const arrowIcon = () => fromMarkup(
  '<svg class="arrow" viewBox="0 0 14 8" fill="none" stroke="currentColor" stroke-width="1.25" aria-hidden="true"><path d="M0 4h12.5M9.5 1l3 3-3 3"/></svg>');

// The Polybius-square "N": a 5x5 cipher grid whose filled cells spell the letter.
const N_GRID = ["X...X", "XX..X", "X.X.X", "X..XX", "X...X"];
function drawMark(svg) {
  let out = "";
  N_GRID.forEach((row, r) => [...row].forEach((ch, c) => {
    const x = c * 8, y = r * 8;
    if (ch === "X") {
      const diag = r === c && r > 0 && r < 4;
      out += `<rect x="${x}" y="${y}" width="6" height="6" rx=".75" fill="var(${diag ? "--signal" : "--ink"})"/>`;
    } else {
      out += `<rect x="${x + .5}" y="${y + .5}" width="5" height="5" rx=".75" fill="none" stroke="var(--rule-strong)"/>`;
    }
  }));
  svg.innerHTML = out;
}

// Specimen plate: a deterministic cipher-grid glyph per tool (empty states).
function specimenArt(seedText) {
  let seed = [...seedText].reduce((a, ch) => (a * 31 + ch.charCodeAt(0)) >>> 0, 7);
  const rand = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296);
  const cols = 9, rows = 6, size = 10, gap = 3;
  const runRow = Math.floor(rand() * rows), runCol = Math.floor(rand() * (cols - 3));
  let cells = "";
  for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
    const x = c * (size + gap), y = r * (size + gap);
    const inRun = r === runRow && c >= runCol && c < runCol + 3;
    if (inRun) cells += `<rect x="${x}" y="${y}" width="${size}" height="${size}" rx="1" fill="var(--signal)"/>`;
    else if (rand() < 0.24) cells += `<rect x="${x}" y="${y}" width="${size}" height="${size}" rx="1" fill="var(--ink-3)"/>`;
    else cells += `<rect x="${x + .5}" y="${y + .5}" width="${size - 1}" height="${size - 1}" rx="1" fill="none" stroke="var(--rule-strong)"/>`;
  }
  const w = cols * (size + gap) - gap, h = rows * (size + gap) - gap;
  return fromMarkup(`<svg viewBox="-1 -1 ${w + 2} ${h + 2}" aria-hidden="true">${cells}</svg>`);
}

// ---------------------------------------------------------------------------
// Data marks
// ---------------------------------------------------------------------------
function confidenceWord(s) {
  return s >= 0.85 ? "very high" : s >= 0.7 ? "high" : s >= 0.55 ? "medium" : "low";
}

// Segmented meter: 20 cells, filled cells carry the value, track is a tint of the same hue.
function meter(score, { word = true } = {}) {
  const lit = Math.round(Math.max(0, Math.min(1, score)) * 20);
  const segs = el("span", { class: "segs", "aria-hidden": "true" });
  for (let i = 0; i < 20; i++) {
    segs.append(el("i", { class: i < lit ? "on" : null, style: i < lit ? `animation-delay:${i * 12}ms` : null }));
  }
  return el("span", { class: "meter", role: "img", "aria-label": `${pct(score)} confidence` },
    segs,
    el("span", { class: "pct" }, pct(score)),
    word ? el("span", { class: "word" }, confidenceWord(score)) : null);
}

// Linear gauge with reference markers (HTML, so labels never scale with width).
function gauge(value, { min = 0, max = 1, refs = [], unit = "" }) {
  const pos = (v) => Math.max(0, Math.min(100, ((v - min) / (max - min)) * 100));
  const g = el("div", { class: "gauge" });
  g.append(el("div", { class: "g-axis" }), el("div", { class: "g-fill", style: `width:${pos(value)}%` }));
  for (const r of refs) {
    const p = pos(r.at);
    const align = p > 82 ? "end" : p < 18 ? "start" : "mid";
    g.append(el("div", { class: `g-ref ${align}`, style: `left:${p}%`, title: `${r.label}: ${r.at}${unit}` },
      el("span", {}, r.label)));
  }
  g.append(el("div", { class: "g-dot", style: `left:${pos(value)}%`, title: `${value}${unit}` }));
  g.append(el("div", { class: "g-ends" }, el("span", {}, String(min)), el("span", {}, `${max}${unit}`)));
  return g;
}

// Reference labels that would overlap at this width drop below the axis, next to
// their own marker, instead of stacking away from it.
function fitGauges(root = document) {
  root.querySelectorAll(".gauge").forEach((g) => {
    const refs = [...g.querySelectorAll(".g-ref")];
    refs.forEach((r) => r.classList.remove("low"));
    const ends = [...g.querySelectorAll(".g-ends span")];
    ends.forEach((e) => { e.style.visibility = ""; });
    let lastRight = -Infinity;
    for (const r of refs) {
      const box = r.querySelector("span").getBoundingClientRect();
      if (box.left < lastRight + 6) r.classList.add("low");
      else lastRight = box.right;
    }
    // A dropped reference label outranks the scale end it would crowd.
    for (const r of refs.filter((x) => x.classList.contains("low"))) {
      const box = r.querySelector("span").getBoundingClientRect();
      for (const e of ends) {
        const eb = e.getBoundingClientRect();
        if (box.right + 6 > eb.left && box.left - 6 < eb.right) e.style.visibility = "hidden";
      }
    }
  });
}
let fitTimer;
window.addEventListener("resize", () => { clearTimeout(fitTimer); fitTimer = setTimeout(() => fitGauges(), 120); });

function table(headers, rows, opts = {}) {
  const thClass = (h) => ["hide-sm", "act", "rank"].filter((c) => (h.cls || "").split(" ").includes(c)).join(" ") || null;
  return el("table", { class: "grid-table" },
    el("thead", {}, el("tr", {}, ...headers.map((h) =>
      el("th", { class: thClass(h), scope: "col" }, h.label ?? h)))),
    el("tbody", {}, ...rows.map((row, i) => {
      const cells = Array.isArray(row) ? row : row.cells;
      const cls = [opts.lead && i === 0 ? "lead" : "", Array.isArray(row) ? "" : row.cls || ""].join(" ").trim();
      return el("tr", { class: cls || null }, ...cells.map((cell, k) => {
        const c = headers[k] && headers[k].cls;
        return el("td", { class: c || null }, cell && cell.nodeType ? cell : (cell ?? ""));
      }));
    })));
}

async function copyText(text, btn) {
  try {
    await navigator.clipboard.writeText(text);
  } catch (e) {
    const ta = el("textarea", { style: "position:fixed;opacity:0" });
    ta.value = text; document.body.append(ta); ta.select();
    try { document.execCommand("copy"); } catch (_) {}
    ta.remove();
  }
  if (!btn) return;
  const label = btn.querySelector(".t");
  btn.classList.add("done");
  btn.replaceChild(icon("check"), btn.querySelector("svg"));
  if (label) label.textContent = "Copied";
  clearTimeout(btn._t);
  btn._t = setTimeout(() => {
    btn.classList.remove("done");
    btn.replaceChild(icon("copy"), btn.querySelector("svg"));
    if (label) label.textContent = btn.dataset.label || "Copy";
  }, 1300);
}
function copyBtn(getText, label = "Copy", { iconOnly = false } = {}) {
  const btn = el("button", { type: "button", class: `btn-quiet${iconOnly ? " icon" : ""}`, "data-label": label,
    "aria-label": `${label}`, title: iconOnly ? label : null },
    icon("copy"), iconOnly ? null : el("span", { class: "t" }, label));
  btn.addEventListener("click", () => copyText(getText(), btn));
  return btn;
}
function output(text, { hero = false } = {}) {
  return el("div", { class: `output${hero ? " hero" : ""}` }, el("pre", {}, text), copyBtn(() => text));
}

// ---------------------------------------------------------------------------
// Tool registry
// ---------------------------------------------------------------------------
const MODULES = [
  { id: "01", name: "Cryptography", tools: ["detect", "decode", "hash", "hashid"] },
  { id: "02", name: "Enumeration", tools: ["codeid", "ports"] },
  { id: "03", name: "OSINT", tools: ["iocs", "defang"] },
];

const CODECS = ["auto", "base64", "base32", "hex", "base58", "ascii85", "base85", "url",
  "html", "quoted_printable", "rot13", "rot47", "atbash", "binary", "decimal",
  "morse", "reverse", "caesar", "xor"];

const TOOLS = {
  detect: {
    title: "Detect",
    desc: "Identify encodings, classical ciphers, and modern cryptography from a string. Entropy and index of coincidence are measured alongside ranked candidates.",
    fields: [{ name: "input", type: "textarea", label: "Payload", placeholder: "Paste an unknown string" }],
    route: "/api/crypt/detect",
    samples: [
      { label: "base64", value: "SGVsbG8gV29ybGQh" },
      { label: "jwt", value: "eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyIjoibmV4dXMifQ.Lf9pXH8Ztl6TeV2Jt8qLqBhw4b9vdo1Gf7Q8l8kQ0wA" },
      { label: "hex", value: "4e65787573206669656c6420696e737472756d656e74" },
      { label: "vigenère", value: "GLB UFNPVML EIXX LUI FHLRVZYHG XTCUR EKX LUIK QJBXB XGJR QBW XIV" },
    ],
    summary: (r) => `${r.candidates.length} candidate${r.candidates.length === 1 ? "" : "s"}`,
    render(r) {
      const m = r.metrics;
      const metrics = el("div", { class: "metrics" },
        el("div", { class: "metric" },
          el("div", { class: "label" }, "Length"),
          el("div", { class: "value" }, r.input_length, el("small", {}, "chars")),
          el("div", { class: "hint" }, `printable ${pct(m.printable_ratio)}`)),
        el("div", { class: "metric" },
          el("div", { class: "label" }, "Entropy"),
          el("div", { class: "value" }, m.entropy.toFixed(2), el("small", {}, "bits/byte")),
          gauge(m.entropy, { min: 0, max: 8, refs: [{ at: 4.2, label: "text" }, { at: 6, label: "base64" }] })),
        el("div", { class: "metric" },
          el("div", { class: "label" }, "Index of coincidence"),
          el("div", { class: "value" }, m.index_of_coincidence.toFixed(4)),
          gauge(m.index_of_coincidence, { min: 0, max: 0.1, refs: [{ at: 0.038, label: "random" }, { at: 0.067, label: "english" }] })));
      if (!r.candidates.length) return el("div", {}, metrics, nil("No known pattern matched this input."));
      return el("div", {}, metrics, table(
        [{ label: "#", cls: "rank" }, { label: "Candidate", cls: "name" }, { label: "Category", cls: "cat hide-sm" }, { label: "Confidence" }],
        r.candidates.map((c, i) => [pad2(i + 1), pretty(c.name), pretty(c.category || ""), meter(c.score)]),
        { lead: true }));
    },
  },
  decode: {
    title: "Decode",
    desc: "Decode with a named codec, or leave it on auto: decoder chains are searched breadth-first and ranked by how readable the result is.",
    fields: [
      { name: "input", type: "textarea", label: "Payload", placeholder: "Paste encoded text" },
      { name: "codec", type: "select", label: "Codec", options: CODECS },
      { name: "shift", type: "number", label: "Caesar shift", value: 3, when: { codec: "caesar" } },
      { name: "key", type: "text", label: "XOR key", placeholder: "repeating key", when: { codec: "xor" } },
    ],
    route: "/api/crypt/decode",
    samples: [
      { label: "nested", value: "Wm14aFozdHVaWGgxYzE5amIyNXpiMnhsZlE9PQ==" },
      { label: "rot13", value: "Uryyb, Jbeyq. Gur synt vf va gur ybtf." },
      { label: "morse", value: ".-- . .-.. -.-. --- -- . / - --- / -. . -..- ..- ..." },
      { label: "binary", value: "01001110 01100101 01111000 01110101 01110011" },
    ],
    summary: (r) => r.mode === "auto" ? `${r.candidates.length} recipe${r.candidates.length === 1 ? "" : "s"}` : `codec ${r.mode}`,
    render(r) {
      if (r.mode !== "auto") return el("div", { class: "readout-body" }, output(r.output, { hero: true }));
      if (!r.candidates.length) return nil("No readable decoding found. Try a specific codec.");
      const chainOf = (recipe) => {
        const chain = el("span", { class: "chain" });
        recipe.forEach((step, k) => { if (k) chain.append(arrowIcon()); chain.append(el("span", { class: "step" }, step)); });
        return chain;
      };
      const [best, ...rest] = r.candidates;
      const view = el("div", { class: "recipes" },
        el("div", { class: "recipe lead" },
          el("div", { class: "recipe-top" },
            el("span", { class: "rank" }, "01"), chainOf(best.recipe), el("span", { class: "badge" }, "Best"),
            el("span", { class: "spacer" }), meter(best.score, { word: false })),
          output(best.output, { hero: true })));
      if (rest.length) {
        view.append(el("div", { class: "subhead" }, el("span", { class: "label" }, "Other recipes"),
          el("span", { class: "code" }, String(rest.length))));
        rest.forEach((c, i) => view.append(el("div", { class: "recipe alt" },
          el("span", { class: "rank" }, pad2(i + 2)), chainOf(c.recipe),
          el("code", { class: "preview", title: c.output }, c.output),
          meter(c.score, { word: false }), copyBtn(() => c.output, "Copy", { iconOnly: true }))));
      }
      return view;
    },
  },
  hash: {
    title: "Hash",
    desc: "Compute common digests of a string: MD5, the SHA-1, SHA-2 and SHA-3 families, BLAKE2, and CRC-32.",
    fields: [{ name: "input", type: "textarea", label: "Text", placeholder: "Text to hash" }],
    route: "/api/crypt/hash",
    samples: [{ label: "text", value: "correct horse battery staple" }, { label: "word", value: "hello" }],
    summary: (r) => `${Object.keys(r.hashes).length} digests`,
    render(r) {
      return table([{ label: "Algorithm", cls: "cat" }, { label: "Digest", cls: "mono wrap" }, { label: "", cls: "act" }],
        Object.entries(r.hashes).map(([k, v]) => [k.replace("_", "-"), v, copyBtn(() => v, `Copy ${k}`, { iconOnly: true })]));
    },
  },
  hashid: {
    title: "Hash ID",
    desc: "Identify the likely algorithm behind a hash from its format, length, and character set.",
    fields: [{ name: "input", type: "text", label: "Hash", placeholder: "5d41402abc4b2a76b9719d911017c592" }],
    route: "/api/crypt/hash-id",
    samples: [
      { label: "md5", value: "5d41402abc4b2a76b9719d911017c592" },
      { label: "sha1", value: "aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d" },
      { label: "sha256", value: "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824" },
      { label: "bcrypt", value: "$2b$12$R9h/cIPz0gi.URNNX3kh2OPST9/PgBkqquzi.Ss7KIUgO2t0jWMUW" },
    ],
    summary: (r) => `${r.candidates.length} match${r.candidates.length === 1 ? "" : "es"}`,
    render(r) {
      if (!r.candidates.length) return nil("Not a recognized hash format.");
      return table([{ label: "#", cls: "rank" }, { label: "Algorithm", cls: "name" }, { label: "Basis", cls: "cat hide-sm" }, { label: "Confidence" }],
        r.candidates.map((c, i) => [pad2(i + 1), c.name, c.basis, meter(c.confidence)]), { lead: true });
    },
  },
  codeid: {
    title: "Code ID",
    desc: "Identify the programming language of a snippet from shebangs and weighted syntax signatures across fourteen languages.",
    fields: [{ name: "input", type: "textarea", label: "Snippet", placeholder: "Paste source code" }],
    route: "/api/enum/code-id",
    samples: [
      { label: "python", value: "import sys\n\ndef main():\n    print(sys.argv)" },
      { label: "go", value: "package main\n\nimport \"fmt\"\n\nfunc main() {\n    fmt.Println(\"hi\")\n}" },
      { label: "rust", value: "fn main() {\n    let mut n = 0;\n    println!(\"{}\", n);\n}" },
    ],
    summary: (r) => `${r.candidates.length} language${r.candidates.length === 1 ? "" : "s"}`,
    render(r) {
      return table([{ label: "#", cls: "rank" }, { label: "Language", cls: "name" }, { label: "Evidence", cls: "cat hide-sm" }, { label: "Confidence" }],
        r.candidates.map((c, i) => [pad2(i + 1), c.language, c.evidence, meter(c.confidence)]), { lead: true });
    },
  },
  ports: {
    title: "Ports",
    desc: "Look up a well-known port by number, or search services by name. The reference table ships with Nexus and works offline.",
    fields: [{ name: "input", type: "text", label: "Port or service", placeholder: "443 or smb" }],
    route: "/api/enum/ports",
    samples: [{ label: "port", value: "443" }, { label: "service", value: "smb" }, { label: "port", value: "3389" }, { label: "service", value: "redis" }],
    summary: (r) => `${r.count} result${r.count === 1 ? "" : "s"}`,
    render(r) {
      if (!r.matches.length) return nil(`No known port or service matches “${r.query}”.`);
      return table([{ label: "Port", cls: "port" }, { label: "Service", cls: "name" }, { label: "Proto", cls: "cat hide-sm" }, { label: "Description" }],
        r.matches.map((m) => [m.port, m.service, m.protocol, m.description]));
    },
  },
  iocs: {
    title: "IOC Extract",
    desc: "Pull indicators out of pasted logs or notes: URLs, domains, IPv4 and IPv6 addresses, email addresses, and hashes.",
    fields: [{ name: "input", type: "textarea", label: "Text", placeholder: "Paste logs, alerts, or notes" }],
    route: "/api/osint/iocs",
    samples: [{ label: "alert", value: "GET http://malware.example.com/payload from 185.23.44.9\ncallback to evil.test.org, operator a@test.org\nsample md5 5d41402abc4b2a76b9719d911017c592" }],
    summary: (r) => `${r.ioc_total} indicator${r.ioc_total === 1 ? "" : "s"}`,
    render(r) {
      const kinds = Object.keys(r.iocs);
      if (!kinds.length) return nil("No indicators found in this text.");
      const tally = el("div", { class: "tally" }, ...kinds.map((k) =>
        el("div", {}, el("span", { class: "label" }, k), el("b", {}, r.iocs[k].length))));
      const rows = kinds.flatMap((k) => r.iocs[k].map((v, i) => ({
        cls: i === 0 ? "group" : null,
        cells: [i === 0 ? k : "", v, copyBtn(() => v, `Copy ${k}`, { iconOnly: true })],
      })));
      return el("div", {}, tally,
        table([{ label: "Type", cls: "cat" }, { label: "Indicator", cls: "mono wrap" }, { label: "", cls: "act" }], rows));
    },
  },
  defang: {
    title: "Defang",
    desc: "Neutralize indicators so they are safe to paste into reports and chat, or restore defanged text back to live form.",
    fields: [
      { name: "input", type: "textarea", label: "Text", placeholder: "http://evil.example.com/x" },
      { name: "mode", type: "select", label: "Mode", options: ["defang", "refang"] },
    ],
    route: "/api/osint/defang",
    samples: [
      { label: "defang", value: "http://malware.example.com/payload from 185.23.44.9", params: { mode: "defang" } },
      { label: "refang", value: "hxxps[://]evil[.]test[.]org/login", params: { mode: "refang" } },
    ],
    summary: (r) => `${r.output.length} chars`,
    render(r) { return el("div", { class: "readout-body" }, output(r.output, { hero: true })); },
  },
};
const ORDER = MODULES.flatMap((m) => m.tools);
const CODE = {};
MODULES.forEach((m) => m.tools.forEach((t, i) => { CODE[t] = { code: `${m.id}.${i + 1}`, module: m.name }; }));

function nil(text) {
  return el("div", { class: "nil" }, el("span", { class: "label" }, "No result"), el("span", {}, text));
}

// ---------------------------------------------------------------------------
// Rail
// ---------------------------------------------------------------------------
function buildRail() {
  const rail = document.getElementById("rail");
  for (const m of MODULES) {
    const group = el("div", { class: "module", role: "group", "aria-labelledby": `m-${m.id}` },
      el("div", { class: "module-head" }, el("span", { class: "code" }, m.id), el("span", { class: "label", id: `m-${m.id}` }, m.name)));
    for (const key of m.tools) {
      group.append(el("button", { class: "tool", type: "button", "data-tool": key, onclick: () => go(key) },
        icon(key), el("span", {}, TOOLS[key].title), el("span", { class: "code" }, CODE[key].code)));
    }
    rail.append(group);
  }
  rail.append(el("div", { class: "rail-note" },
    el("div", { class: "module-head" }, el("span", { class: "code" }, "04"), el("span", { class: "label" }, "Logs")),
    "Ingest and query JSONL from the terminal with ", el("code", {}, "nexus log"), "."));
  const mod = isMac ? "⌘" : "Ctrl";
  rail.append(el("div", { class: "rail-foot" }, el("div", { class: "keys" },
    el("span", {}, el("kbd", {}, mod), el("kbd", {}, "↵")), el("span", {}, "Run"),
    el("span", {}, el("kbd", {}, "/")), el("span", {}, "Focus input"),
    el("span", {}, el("kbd", {}, "["), el("kbd", {}, "]")), el("span", {}, "Previous / next tool"))));
}

// ---------------------------------------------------------------------------
// Workbench
// ---------------------------------------------------------------------------
const drafts = {};
let current = null;

function buildField(f, key) {
  const id = `f-${key}-${f.name}`;
  let input;
  if (f.type === "textarea") {
    input = el("textarea", { id, name: f.name, placeholder: f.placeholder || "", spellcheck: "false", autocomplete: "off" });
  } else if (f.type === "select") {
    input = el("select", { id, name: f.name }, ...f.options.map((o) => el("option", { value: o }, o)));
  } else {
    input = el("input", { id, type: f.type === "number" ? "number" : "text", name: f.name, spellcheck: "false",
      autocomplete: "off", placeholder: f.placeholder || "", value: f.value != null ? f.value : "" });
  }
  const counter = f.name === "input" ? el("span", { class: "code num", "aria-hidden": "true" }, "0 chars") : null;
  if (counter) input.addEventListener("input", () => { counter.textContent = `${[...input.value].length} chars`; });
  return { wrap: el("div", { class: "field" }, el("label", { class: "label", for: id }, f.label, counter), input), input, counter };
}

function showTool(key) {
  const tool = TOOLS[key];
  current = key;
  document.querySelectorAll(".tool").forEach((b) => {
    if (b.dataset.tool === key) { b.setAttribute("aria-current", "page"); b.scrollIntoView({ block: "nearest", inline: "nearest" }); }
    else b.removeAttribute("aria-current");
  });
  document.title = `${tool.title} · Nexus Console`;

  const panel = document.getElementById("panel");
  panel.replaceChildren();

  const inputs = {};
  let counter = null;
  const big = tool.fields.filter((f) => f.type === "textarea" || (f.name === "input" && tool.fields.length === 1));
  const small = tool.fields.filter((f) => !big.includes(f));

  const body = el("div", { class: "panel-body" });
  for (const f of big) { const b = buildField(f, key); inputs[f.name] = b.input; counter = b.counter || counter; body.append(b.wrap); }
  const controls = el("div", { class: "controls" });
  const params = el("div", { class: "params" });
  const conditional = [];
  for (const f of small) {
    const b = buildField(f, key); inputs[f.name] = b.input; params.append(b.wrap);
    if (f.when) conditional.push([b.wrap, f.when]);
  }
  controls.append(params);
  const runBtn = el("button", { class: "btn", type: "button" },
    el("span", { class: "t" }, "Run"), el("kbd", {}, isMac ? "⌘ ↵" : "Ctrl ↵"));
  controls.append(el("div", { class: "btn-wrap" }, runBtn));
  if (!small.length) params.append(el("span", { class: "label assurance" }, "Processed locally. Nothing leaves this machine."));
  body.append(controls);
  const syncConditional = () => conditional.forEach(([wrap, when]) => {
    wrap.hidden = !Object.entries(when).every(([k, v]) => inputs[k] && inputs[k].value === v);
  });

  // Restore the previous draft for this tool.
  const draft = drafts[key];
  if (draft) for (const [k, v] of Object.entries(draft)) if (inputs[k]) inputs[k].value = v;
  if (counter) counter.textContent = `${[...(inputs.input.value || "")].length} chars`;
  Object.values(inputs).forEach((inp) => inp.addEventListener("input", syncConditional));
  Object.values(inputs).forEach((inp) => inp.addEventListener("change", syncConditional));
  syncConditional();
  Object.entries(inputs).forEach(([k, inp]) => inp.addEventListener("input", () => {
    drafts[key] = drafts[key] || {}; drafts[key][k] = inp.value;
  }));

  const inputPanel = el("section", { class: "panel", "aria-label": "Input" },
    el("div", { class: "panel-head" }, el("span", { class: "label" }, "Input"), el("span", { class: "spacer" }),
      el("span", { class: "meta" }, `POST ${tool.route}`)),
    body);

  const metaRight = el("span", { class: "meta num", "aria-live": "polite" });
  const actions = el("span", {});
  const readoutBody = el("div", { class: "readout-content" });
  const readout = el("section", { class: "panel reg readout", "aria-label": "Readout" },
    el("div", { class: "scan", "aria-hidden": "true" }),
    el("div", { class: "panel-head" }, el("span", { class: "label" }, "Readout"), el("span", { class: "spacer" }), metaRight, actions),
    readoutBody);

  function setEmpty() {
    metaRight.textContent = "idle";
    actions.replaceChildren();
    const samples = el("div", { class: "samples" }, ...tool.samples.map((s) =>
      el("button", { type: "button", class: "sample", title: s.value, onclick: () => loadSample(s) },
        el("span", { class: "label" }, s.label), s.value.split("\n")[0])));
    readoutBody.replaceChildren(el("div", { class: "specimen" }, specimenArt(key),
      el("div", {}, el("h2", {}, "Awaiting input"),
        el("p", {}, "Paste a payload above and run it, or load one of these specimens."), samples)));
  }

  function loadSample(s) {
    inputs.input.value = s.value;
    for (const [k, v] of Object.entries(s.params || {})) if (inputs[k]) inputs[k].value = v;
    inputs.input.dispatchEvent(new Event("input"));
    for (const k of Object.keys(s.params || {})) if (inputs[k]) inputs[k].dispatchEvent(new Event("input"));
    run();
  }

  let inflight = 0;
  async function run() {
    const body = {};
    for (const [k, inp] of Object.entries(inputs)) body[k] = inp.value;
    if (!String(body.input || "").trim()) { inputs.input.focus(); return; }
    const ticket = ++inflight;
    readout.classList.add("busy");
    readout.setAttribute("aria-busy", "true");
    runBtn.disabled = true; runBtn.querySelector(".t").textContent = "Reading";
    metaRight.textContent = "reading…";
    const t0 = performance.now();
    let data, failure = null;
    try {
      const res = await fetch(tool.route, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      data = await res.json();
      if (data && data.error) failure = data.error;
    } catch (e) {
      failure = `request failed: ${e.message || e}. Is nexus serve still running?`;
    }
    if (ticket !== inflight) return;
    const ms = Math.max(1, Math.round(performance.now() - t0));
    readout.classList.remove("busy");
    readout.removeAttribute("aria-busy");
    runBtn.disabled = false; runBtn.querySelector(".t").textContent = "Run";
    if (failure) {
      metaRight.textContent = `${ms} ms`;
      actions.replaceChildren();
      readoutBody.replaceChildren(el("div", { class: "fault", role: "alert" }, el("span", { class: "mark", "aria-hidden": "true" }),
        el("div", {}, el("span", { class: "label" }, "Error"), el("span", { class: "msg" }, failure))));
      return;
    }
    metaRight.textContent = `${tool.summary(data)} · ${ms} ms`;
    actions.replaceChildren(copyBtn(() => JSON.stringify(data, null, 2), "JSON"));
    const view = tool.render(data);
    view.classList.add("reveal");
    readoutBody.replaceChildren(view);
    requestAnimationFrame(() => fitGauges(view));
  }

  runBtn.addEventListener("click", run);
  inputPanel.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); run(); }
  });
  setEmpty();

  const c = CODE[key];
  panel.append(
    el("header", { class: "tool-head" },
      el("div", { class: "eyebrow" }, el("span", { class: "code" }, c.code), el("span", { class: "bar" }), el("span", { class: "label" }, c.module)),
      el("h1", {}, tool.title), el("p", {}, tool.desc)),
    inputPanel, readout,
    el("footer", { class: "colophon" },
      el("span", { class: "label" }, `Nexus ${window.NEXUS_VERSION || ""}`.trim()),
      el("span", { class: "label" }, "No telemetry"),
      el("span", { class: "label" }, "All processing on this machine")));
  return inputs;
}

function go(key) {
  if (location.hash.slice(1) !== key) location.hash = key; else route();
}
function route() {
  const key = location.hash.slice(1);
  const inputs = showTool(TOOLS[key] ? key : "detect");
  const first = inputs && inputs.input;
  if (first && window.matchMedia("(min-width: 761px)").matches) first.focus({ preventScroll: true });
}

// ---------------------------------------------------------------------------
// Theme
// ---------------------------------------------------------------------------
function applyTheme(t) {
  document.documentElement.setAttribute("data-theme", t);
  document.querySelectorAll("[data-theme-set]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.themeSet === t)));
  const meta = document.querySelectorAll('meta[name="theme-color"]');
  meta.forEach((m) => m.setAttribute("content", t === "carbon" ? "#1A1A18" : "#F7F6F1"));
}
function initTheme() {
  applyTheme(document.documentElement.getAttribute("data-theme") || "paper");
  document.querySelectorAll("[data-theme-set]").forEach((b) => b.addEventListener("click", () => {
    applyTheme(b.dataset.themeSet);
    try { localStorage.setItem("nexus.theme", b.dataset.themeSet); } catch (e) {}
  }));
}

// ---------------------------------------------------------------------------
// Keyboard
// ---------------------------------------------------------------------------
document.addEventListener("keydown", (e) => {
  const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement && document.activeElement.tagName);
  if (typing || e.ctrlKey || e.metaKey || e.altKey) return;
  if (e.key === "/") {
    const t = document.querySelector("#panel textarea, #panel input");
    if (t) { e.preventDefault(); t.focus(); }
  } else if (e.key === "[" || e.key === "]") {
    const i = ORDER.indexOf(current);
    go(ORDER[(i + (e.key === "]" ? 1 : -1) + ORDER.length) % ORDER.length]);
  }
});

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------
async function init() {
  drawMark(document.getElementById("brand-mark"));
  document.getElementById("origin").textContent = location.host;
  initTheme();
  buildRail();
  try {
    const meta = await (await fetch("/api/meta")).json();
    if (meta.version) {
      window.NEXUS_VERSION = meta.version;
      document.getElementById("version").textContent = meta.version;
    }
  } catch (e) { /* offline-safe */ }
  window.addEventListener("hashchange", route);
  route();
}

init();
