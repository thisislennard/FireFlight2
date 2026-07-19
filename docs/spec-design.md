# FireFlight2 – Design-Spezifikation (Nutzer-Vorgabe)

Extrahiert aus dem vom Nutzer gelieferten "FireFlight2 Design Guide" (claude.ai Design-Tool-Export) vom 2026-07-19. Enthält die tatsächlich relevanten Design-Inhalte (Tokens, Komponenten-CSS, Beschreibungstexte) — Bundler-Runtime, Font-Binärdaten und React-Bundles aus dem Original-Export wurden nicht übernommen, da irrelevant für die Umsetzung. Referenz-Dokument — Zusammenfassung in `CLAUDE.md`.

Design-System-Name (intern im Export): **"Modernist"** — flach, scharfe Kanten (0px Radius durchgehend), eine Akzentfarbe, Archivo-Schrift.

## Logo
Dunkles Badge (`#181514`, immer fix — unabhängig vom Hell-/Dunkelmodus) mit Drohnen-Liniensymbol und Flammen-Icon in der Akzentfarbe. Mindestgröße 28×28px, Freiraum mind. 25% der Badge-Breite auf allen Seiten. Immer auf dunklem Grund — nie auf hellen Flächen frei stehend.

Inline-SVG (kein externes Asset, wie v1s Landingpage-Drohne):
```html
<div style="width:44px; height:44px; background:#181514; display:flex; align-items:center; justify-content:center;">
  <svg width="30" height="30" viewBox="0 0 48 48" aria-hidden="true">
    <rect x="19" y="13" width="10" height="6" rx="2" fill="none" stroke="var(--color-accent)" stroke-width="2.2"/>
    <line x1="20" y1="14" x2="11" y2="8" stroke="var(--color-accent)" stroke-width="2.2"/>
    <line x1="11" y1="8" x2="6" y2="4" stroke="var(--color-accent)" stroke-width="2.2"/>
    <line x1="11" y1="8" x2="9" y2="11" stroke="var(--color-accent)" stroke-width="2.2"/>
    <line x1="28" y1="14" x2="37" y2="8" stroke="var(--color-accent)" stroke-width="2.2"/>
    <line x1="37" y1="8" x2="42" y2="4" stroke="var(--color-accent)" stroke-width="2.2"/>
    <line x1="37" y1="8" x2="39" y2="11" stroke="var(--color-accent)" stroke-width="2.2"/>
    <circle cx="6" cy="4" r="1.8" fill="var(--color-accent)"/>
    <circle cx="9" cy="11" r="1.8" fill="var(--color-accent)"/>
    <circle cx="42" cy="4" r="1.8" fill="var(--color-accent)"/>
    <circle cx="39" cy="11" r="1.8" fill="var(--color-accent)"/>
    <g transform="translate(12,18)">
      <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z" fill="var(--color-accent)"/>
    </g>
  </svg>
</div>
```

## Farben
Heller Grund (`#f3f2f2`), dunkle Schrift (`#201e1d`), ein Akzent Rot-Orange (`#ec3013`), sekundärer Akzent `#e15b47`. Jede Farbrolle hat eine 100–900-Tonrampe (generiert in OKLCH auf einer gemeinsamen Helligkeitsskala, damit gleiche Stufen über alle Rollen hinweg im selben visuellen "Wert" liegen): 100–300 für Flächen/Tags, 500 als Basisfarbe, 700–900 für Text auf getönten Flächen.

### Status-/Alarmfarben
Das System ist bewusst monochrom (ein Akzent). Status wird **nie über Farbton**, sondern über **Füllstärke + Text + Icon** codiert — barrierefrei und im Stil des Systems:
- **Gefüllt Rot** — aktiv / läuft / Alarm
- **Outline Rot** — Standby / geplant / Warnung
- **Grau** — abgeschlossen / verfügbar / Info

**Offen:** Exakte Dark-Mode-Farbwerte waren im gelieferten Guide nicht enthalten (nur die Beschreibung, dass `--color-bg`/`--color-surface`/`--color-text`/`--color-divider`/`--color-neutral-100`/`--color-neutral-200` am Wurzelelement überschrieben werden, Akzentton bleibt in beiden Modi identisch). Muss beim Umsetzen der Dark-Mode-Variante abgeleitet oder beim Nutzer nachgefragt werden.

## Typografie
**Archivo**, eine Schriftfamilie für alles (Google Font, self-hosted, Gewichte 400/600/800, Subsets latin/latin-ext/vietnamese). Überschriften: Archivo 800. Fließtext: Archivo 400. Zahlen (Akku %, Höhe, Geschwindigkeit) immer mit `font-variant-numeric: tabular-nums`, damit Werte nicht springen.

Scale: H1 42px, H2 32px, H3 25px, H4 20px, H5 16px, H6 13px (uppercase, letter-spacing 0.08em), Body 15px/1.55.

## Buttons
Primär = gefüllt, genau **eine** pro Ansicht/Karte für die wichtigste Aktion. Sekundär = Rahmen, für Nebenaktionen. Ghost = textstark, für unauffällige Aktionen. Icon-Buttons quadratisch, 36×36px. Labels immer linksbündig, nie zentriert.

## Tags
Status-Labels: Aktiv (`tag-accent`, gefüllt), Standby (`tag-outline`), Abgeschlossen (`tag-neutral`).

## Karten
Nutzen `--color-surface`, Kanten scharf (0px Radius). Drei Elevation-Stufen: `elev-sm` für ruhige Listen, `elev-md` für Standard-Dashboard-Karten, `elev-lg` für die aktive Steuerungskarte/Modals.

## Formulare
Textfeld (`.input`), Segmented Control (`.seg`) für Auswahl mit wenigen Optionen, Radio (`.radio`) für Einzelauswahl.

## Icons
**Lucide** (lucide.dev), konsequent — Strichstärke 2px, `currentColor`. Größe 15–18px inline, 26–32px als Badge. Nie gemischt mit anderen Icon-Stilen.

## Navigation & Layout
Desktop: feste Sidebar links (220px) mit Icon + Label. Handy (<760px): Sidebar wird zur fixen Bottom-Tab-Bar, Labels werden ausgeblendet, Karten-Grids fallen auf eine Spalte, Telemetrie-Kacheln auf zwei Spalten. **Kein separates Mobile-Design** — dieselben Komponenten, andere Anordnung.

## Darkmode
Nutzerwahl, nicht erzwungen. Sonne/Mond-Icon oben rechts schaltet um. Technisch: Farb-Variablen werden am Wurzelelement überschrieben — der Akzentton bleibt in beiden Modi identisch, damit Alarmfarben konsistent erkennbar sind.

---

## CSS — Design-Tokens (vollständig, wörtlich aus dem Guide)

```css
:root {
  --color-bg: #f3f2f2;
  --color-surface: #eae9e9;
  --color-text: #201e1d;
  --color-accent: #ec3013;
  --color-accent-2: #e15b47;
  --color-divider: color-mix(in srgb, #201e1d 40%, transparent);

  /* Tonal ramps — generiert in OKLCH auf einer gemeinsamen Helligkeitsskala */
  --color-neutral-100: #f8f4f4;
  --color-neutral-200: #eae7e7;
  --color-neutral-300: #d7d3d3;
  --color-neutral-400: #bab6b6;
  --color-neutral-500: #9b9797;
  --color-neutral-600: #7d7979;
  --color-neutral-700: #605d5d;
  --color-neutral-800: #444141;
  --color-neutral-900: #2d2b2b;

  --color-accent-100: #fff2ef;
  --color-accent-200: #ffe0d9;
  --color-accent-300: #ffc4b8;
  --color-accent-400: #ff9783;
  --color-accent-500: #ff563c;
  --color-accent-600: #dd2b0f;
  --color-accent-700: #ae1800;
  --color-accent-800: #7c1405;
  --color-accent-900: #4d170e;

  --color-accent-2-100: #fff2ef;
  --color-accent-2-200: #ffe0da;
  --color-accent-2-300: #ffc4b9;
  --color-accent-2-400: #ff9784;
  --color-accent-2-500: #ef6853;
  --color-accent-2-600: #c94b39;
  --color-accent-2-700: #9e3526;
  --color-accent-2-800: #71261b;
  --color-accent-2-900: #471d16;

  --font-heading: "Archivo", system-ui, sans-serif;
  --font-heading-weight: 800;
  --font-body: "Archivo", system-ui, sans-serif;

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-6: 24px;
  --space-8: 32px;

  --radius-sm: 0px;
  --radius-md: 0px;
  --radius-lg: 0px;

  /* Elevation — ink-getönte Schatten, abgeleitet vom Neutral-900-Grundton */
  --shadow-sm: 0 1px 2px color-mix(in srgb, #2d2b2b 14%, transparent);
  --shadow-md: 0 3px 10px color-mix(in srgb, #2d2b2b 16%, transparent);
  --shadow-lg: 0 12px 32px color-mix(in srgb, #2d2b2b 22%, transparent);
}

body { background: var(--color-bg); color: var(--color-text); font-family: var(--font-body); }
h1, h2, h3, h4 { font-family: var(--font-heading); font-weight: var(--font-heading-weight); }

*, *::before, *::after { box-sizing: border-box; }
body { margin: 0; font-size: 15px; line-height: 1.55; font-weight: 400; }
h1, h2, h3, h4, h5, h6 {
  font-family: var(--font-heading); font-weight: var(--font-heading-weight);
  line-height: 1.12; letter-spacing: -0.015em; margin: 0 0 var(--space-2);
}
h1 { font-size: 42px; }
h2 { font-size: 32px; }
h3 { font-size: 25px; }
h4 { font-size: 20px; }
h5 { font-size: 16px; }
h6 { font-size: 13px; letter-spacing: 0.08em; text-transform: uppercase; }
p { margin: 0 0 var(--space-3); }
a { color: var(--color-accent); text-underline-offset: 3px; }
img { display: block; max-width: 100%; }
.text-muted { color: color-mix(in srgb, var(--color-text) 55%, transparent); }
:focus { outline: none; }
:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
::selection { background: color-mix(in srgb, var(--color-accent) 30%, transparent); }

.hr { height: 2px; border: 0; margin: var(--space-4) 0; background: var(--color-divider); }

/* Buttons */
.btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  cursor: pointer; text-decoration: none;
  font-family: var(--font-heading); font-weight: var(--font-heading-weight);
  font-size: 14px; line-height: 1.2; color: var(--color-text);
  background: transparent; border: 1px solid transparent;
  padding: var(--space-2) calc(var(--space-3) * 1.2);
  border-radius: var(--radius-md);
}
.btn svg { display: block; }
.btn:disabled { opacity: 0.45; cursor: not-allowed; }
.btn-primary { background: var(--color-accent); color: var(--color-bg); }
.btn-primary:hover { background: var(--color-accent-600); }
.btn-primary:active { background: var(--color-accent-700); }
.btn-secondary { border-color: var(--color-divider); }
.btn-secondary:hover { background: color-mix(in srgb, var(--color-text) 7%, transparent); }
.btn-secondary:active { background: color-mix(in srgb, var(--color-text) 14%, transparent); }
.btn-ghost { color: var(--color-accent); padding-inline: var(--space-1); }
.btn-ghost:hover { background: color-mix(in srgb, var(--color-accent) 10%, transparent); }
.btn-ghost:active { background: color-mix(in srgb, var(--color-accent) 18%, transparent); }
.btn-icon { width: 36px; height: 36px; padding: 0; }
.btn-block { width: 100%; margin-top: var(--space-2); justify-content: flex-start; text-align: left; }

/* Formulare */
.field > label { display: block; font-size: 12px; margin-bottom: 5px; color: color-mix(in srgb, var(--color-text) 70%, transparent); }
.input {
  width: 100%; min-height: 36px; padding: 6px 10px; font: inherit;
  font-size: 14px; color: var(--color-text); caret-color: var(--color-accent);
  background: var(--color-surface);
  border: 1px solid var(--color-divider); border-radius: var(--radius-md);
}
.input:hover { border-color: color-mix(in srgb, var(--color-text) 45%, transparent); }
.input:focus-visible { border-color: var(--color-accent); outline-offset: 0; }
textarea.input { min-height: 90px; resize: vertical; }
.radio { display: inline-flex; align-items: center; gap: 8px; cursor: pointer; font-size: 14px; }
.radio input, .seg-opt input { position: absolute; opacity: 0; width: 0; height: 0; pointer-events: none; }
.radio .dot { width: 16px; height: 16px; flex: none; border-radius: 50%; border: 1.5px solid var(--color-divider); }
.radio:hover .dot { border-color: var(--color-accent); }
.radio input:checked + .dot { border-color: var(--color-accent); background: var(--color-accent); box-shadow: inset 0 0 0 4px var(--color-bg); }
.radio input:focus-visible + .dot { outline: 2px solid var(--color-accent); outline-offset: 2px; }
.seg { display: inline-flex; overflow: hidden; border: 1px solid var(--color-divider); border-radius: var(--radius-md); }
.seg-opt { display: inline-flex; align-items: center; gap: 6px; padding: 7px 12px; font-size: 13px; cursor: pointer; }
.seg-opt + .seg-opt { border-left: 1px solid var(--color-divider); }
.seg-opt:has(input:checked) { background: var(--color-accent); color: var(--color-bg); }
.seg-opt:not(:has(input:checked)):hover { background: color-mix(in srgb, var(--color-text) 7%, transparent); }
.seg-opt:has(input:focus-visible) { outline: 2px solid var(--color-accent); outline-offset: -2px; }

/* Karten */
.card { display: flex; flex-direction: column; gap: var(--space-2); padding: var(--space-3); border-radius: var(--radius-md); background: var(--color-surface); }
.card-kicker { font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--color-accent); }
.card-title { font-family: var(--font-heading); font-weight: var(--font-heading-weight); font-size: 17px; line-height: 1.2; }
.card-body { margin: 0; font-size: 13px; opacity: 0.8; flex: 1; }
.card-meta { display: flex; align-items: center; gap: 6px; font-size: 11px; color: color-mix(in srgb, var(--color-text) 50%, transparent); }
.elev-sm { box-shadow: var(--shadow-sm); }
.elev-md { box-shadow: var(--shadow-md); }
.elev-lg { box-shadow: var(--shadow-lg); }

/* Tags */
.tag { display: inline-flex; align-items: center; font-size: 11px; letter-spacing: 0.02em; padding: 3px 10px; border-radius: calc(var(--radius-md) * 0.75); }
.tag-accent { background: var(--color-accent-100); color: var(--color-accent-800); }
.tag-accent-2 { background: var(--color-accent-2-100); color: var(--color-accent-2-800); }
.tag-neutral { background: var(--color-neutral-100); color: var(--color-neutral-800); }
.tag-outline { border: 1px solid var(--color-accent); color: var(--color-accent); }

/* Navigation */
.nav { display: flex; align-items: center; gap: var(--space-4); padding: var(--space-3) var(--space-4); border-bottom: 2px solid var(--color-divider); }
.nav-brand { font-family: var(--font-heading); font-weight: var(--font-heading-weight); font-size: 18px; margin-right: auto; }
.nav a { color: inherit; text-decoration: none; font-size: 14px; }
.nav a:hover, .nav a[aria-current='page'] { color: var(--color-accent); }

/* Tabellen */
.table { width: 100%; border-collapse: collapse; font-size: 14px; }
.table th { text-align: left; font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: color-mix(in srgb, var(--color-text) 60%, transparent); padding: var(--space-2); border-bottom: 2px solid var(--color-divider); }
.table td { padding: var(--space-2); border-bottom: 1px solid var(--color-divider); }
.table tbody tr:hover { background: color-mix(in srgb, var(--color-text) 4%, transparent); }

/* Dialog */
.dialog-backdrop { position: fixed; inset: 0; display: grid; place-items: center; padding: var(--space-4); background: color-mix(in srgb, var(--color-neutral-900) 50%, transparent); }
.dialog { width: min(440px, 100%); display: flex; flex-direction: column; gap: var(--space-3); padding: var(--space-4); border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-lg); }
.dialog-title { font-family: var(--font-heading); font-weight: var(--font-heading-weight); font-size: 20px; }
.dialog-body { font-size: 14px; opacity: 0.85; }
.dialog-actions { display: flex; justify-content: flex-end; gap: var(--space-2); margin-top: var(--space-2); }
```

## Umsetzungshinweise für FireFlight2
- Font "Archivo" reguär über [Google Fonts](https://fonts.google.com/specimen/Archivo) selbst hosten (Gewichte 400/600/800, `font-display: swap`), lokal unter `app/static/fonts/` vendoren wie v1 Leaflet lokal vendored hat — keine CDN-Abhängigkeit.
- `color-mix(in srgb, ...)` ist modernes CSS (Baseline seit 2023, alle aktuellen Browser) — kein Fallback nötig, passt zum "kein Legacy-Ballast"-Ansatz der Neuentwicklung.
- Icons: [Lucide](https://lucide.dev) als statische SVG-Sprites oder einzeln inline einbinden (kein Icon-Font, kein JS-Icon-Paket nötig bei Server-Rendering).
- Sidebar-Verhalten (220px Desktop, Bottom-Tab-Bar <760px) passt zum Rollen-Navigationskonzept aus `spec-struktur.md` Abschnitt 12.
