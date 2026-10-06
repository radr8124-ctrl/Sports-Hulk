# Sports HULK Theme

## Compact token summary
- Framework: React 18 + Vite 6 + Tailwind CSS 3.4
- Typography: Inter with ui-sans-serif/system fallbacks.
- Base canvas: slate-50 `#f8fafc`.
- Main text: slate-950 / slate-900; supporting text: slate-500/400.
- Primary accent: blue-700, used for active intelligence labels, links, and emphasis.
- Success accent: emerald-500/700 and emerald-50 backgrounds.
- Warning accent: amber-50/amber-200/amber-950.
- Error accent: rose-50/rose-200/rose-800.
- Assistant surface: deep green-black gradients with cyan/emerald accents.
- Cards: white, slate-200 border, large rounded corners (rounded-2xl/3xl), subtle custom `shadow-soft`.
- Hero: white card, rounded ~30px, large black headline with blue second line.
- Layout max width: 1500px with 20px side padding.
- Main vertical rhythm: `space-y-8`.
- Navigation: sticky white brand header + second white horizontal tab bar.
- Breakpoints: Tailwind defaults; common changes at sm, md, lg, xl.
- Motion: minimal hover lift and color transitions; no major page transitions.
- Scrollbars: 8px rounded slate-300 thumb.
- Dark styling is isolated to Ask Sports HULK and the Learning Loop diagnostic block; the primary app is light.

## Raw `tailwind.config.js`
```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      boxShadow: {
        soft: '0 18px 45px rgba(15, 23, 42, 0.08)',
      },
    },
  },
  plugins: [],
}

```

## Raw `src/styles.css`
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: #0f172a;
  background: #f8fafc;
  font-synthesis: none;
  text-rendering: optimizeLegibility;
}

* { box-sizing: border-box; }
html { background: #f8fafc; }
body { margin: 0; min-width: 320px; min-height: 100vh; }
button { font: inherit; }

@layer components {
  .eyebrow {
    @apply text-xs font-black uppercase tracking-[0.18em] text-blue-700;
  }

  .section-heading {
    @apply mb-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-end;
  }

  .section-heading h2 {
    @apply mt-1 text-2xl font-black tracking-tight text-slate-950 md:text-3xl;
  }

  .health-pill {
    @apply inline-flex w-fit rounded-full border border-blue-100 bg-blue-50 px-3 py-1.5 text-xs font-black text-blue-700;
  }

  .health-pill.emerald {
    @apply border-emerald-100 bg-emerald-50 text-emerald-700;
  }
}

@layer components {
  .mini-metric {
    @apply flex min-h-24 flex-col justify-between rounded-2xl border border-slate-200 bg-slate-50 p-4 text-slate-500;
  }

  .mini-metric svg {
    @apply text-blue-700;
  }

  .mini-metric b {
    @apply mt-3 text-sm font-black text-slate-900;
  }

  .mini-metric span {
    @apply text-xs font-semibold text-slate-400;
  }
}

::-webkit-scrollbar { height: 8px; width: 8px; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 999px; }
::-webkit-scrollbar-track { background: transparent; }


@layer components {
  .ask-shell {
    background:
      radial-gradient(circle at 18% 0%, rgba(16,185,129,.12), transparent 30%),
      radial-gradient(circle at 85% 8%, rgba(14,165,233,.12), transparent 28%),
      linear-gradient(180deg, #03100d 0%, #061512 45%, #08110f 100%);
  }

  .ask-shell::before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    background:
      linear-gradient(rgba(255,255,255,.012) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,.012) 1px, transparent 1px);
    background-size: 28px 28px;
    mask-image: linear-gradient(to bottom, rgba(0,0,0,.65), transparent 70%);
  }

  .ask-mini-card {
    @apply rounded-2xl border border-white/10 bg-white/[.035] p-4;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.025);
  }

  .ask-mini-top {
    @apply flex items-center justify-between gap-3 text-[10px] font-black uppercase tracking-[0.14em] text-cyan-300;
  }

  .ask-rail-card {
    @apply rounded-3xl border border-white/10 bg-[#071311]/95 p-5 text-white;
    box-shadow: 0 20px 60px rgba(0,0,0,.28), inset 0 1px 0 rgba(255,255,255,.025);
  }
}

```
