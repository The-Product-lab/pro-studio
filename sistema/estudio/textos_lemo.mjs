// Lee los textos en pantalla de una película de Lemo: node estudio/textos_lemo.mjs <lemo> <carpeta-con-index.html> <salida.json> [--step 0.1] [--size 1080x1920] [--q k=v]
// Usa el motor de Lemo (core/render/page.mjs, sin GL como events.mjs) y el contrato `window.TEXTS(t)` ({id, text, x0..y1}).
// Salida: {"dur", "paso", "textos": [{"id", "text", "t0", "t1"}]}: cada texto con el primer y último instante (paso incluido) en que estuvo en pantalla.
import fs from 'fs'; import path from 'path'; import { pathToFileURL } from 'url';
const args = process.argv.slice(2), opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const [lemo, dir, out] = args;
if (!lemo || !dir || !out) { console.error('uso: textos_lemo.mjs <lemo> <carpeta> <salida.json> [--step 0.1] [--size 1080x1920] [--q k=v]'); process.exit(2); }
const STEP = +opt('--step', 0.1), m = /^(\d+)x(\d+)$/.exec(opt('--size', '1080x1920'));
if (!(STEP > 0) || !m) { console.error('--step o --size inválidos'); process.exit(2); }
const { openDemo, closeServer } = await import(pathToFileURL(path.join(lemo, 'core/render/page.mjs')).href);
const { browser, page } = await openDemo(path.resolve(dir), { w: +m[1], h: +m[2], q: opt('--q', ''), gl: false });   // lee cajas de texto, no dibuja
const res = await page.evaluate(({ STEP }) => {
  if (typeof window.TEXTS !== 'function') return { sinTexts: true };
  const vistos = {};
  for (let t = 0; t <= window.DUR + 1e-9; t += STEP) {
    window.render(t);
    for (const b of window.TEXTS(t) || []) {
      const k = String(b.id) + '\u0000' + b.text;
      const v = vistos[k] ??= { id: String(b.id), text: String(b.text), t0: t, t1: t };
      v.t1 = t;
      for (const [c, f] of [['x0', Math.min], ['y0', Math.min], ['x1', Math.max], ['y1', Math.max]])   // la caja que ocupó en todo su tiempo
        if (Number.isFinite(+b[c])) v[c] = v[c] === undefined ? +b[c] : f(v[c], +b[c]);
    }
  }
  return { dur: window.DUR, textos: Object.values(vistos) };
}, { STEP });
await browser.close(); closeServer();
if (res.sinTexts) { console.error('la película no tiene window.TEXTS(t): no cumple el contrato de Lemo'); process.exit(2); }
for (const x of res.textos) { x.t0 = +x.t0.toFixed(3); x.t1 = +(x.t1 + STEP).toFixed(3); }
fs.writeFileSync(out, JSON.stringify({ dur: res.dur, paso: STEP, textos: res.textos }));
console.log('textos', res.textos.length, '→', out);
