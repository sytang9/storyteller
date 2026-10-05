// Teaser tour recorder: node record_tour.cjs <tour.spec.json> <beats.timed.json> <outdir>
// For each UI beat: run its actions, wait for scrolling to stop, and save a 2x still of the settled page with the
// box of the block around the target text (box) and of the text itself (text). A click also saves a 'before' still
// with the click point. Every non-GET request is aborted except the paths in allow_writes_to (login, token refresh).
// Playwright comes from the caller's install: run with NODE_PATH pointing at a node_modules that holds it.
const { chromium } = require('playwright');
const fs = require('fs');
const [spec, beats, OUT] = [JSON.parse(fs.readFileSync(process.argv[2])), JSON.parse(fs.readFileSync(process.argv[3])), process.argv[4]];
const W = 1920, H = 1080, PAD = 0.6, DSF = 2;
(async () => {
  fs.mkdirSync(OUT + '/frames', { recursive: true });
  fs.mkdirSync(OUT + '/frames', { recursive: true });
  const b = await chromium.launch(process.env.CHROME ? { executablePath: process.env.CHROME } : {});
  const ctx = await b.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: DSF });
  const blocked = [];
  await ctx.route('**/*', r => { const q = r.request(), m = q.method();
    if (!['GET', 'HEAD', 'OPTIONS'].includes(m) && !(spec.allow_writes_to || []).some(a => q.url().includes(a))) { blocked.push(m + ' ' + new URL(q.url()).pathname); return r.abort(); }
    return r.continue(); });
  await ctx.addInitScript("addEventListener('DOMContentLoaded',()=>{document.documentElement.style.zoom='" + (spec.zoom || 1) + "'})");
  const p = await ctx.newPage();
  if (spec.login) {
    const [u,, pw] = fs.readFileSync(spec.login.users_file, 'utf8').trim().split('\n').map(l => l.split('\t')).find(r => r[0] === spec.login.user);
    await p.goto(spec.base + spec.login.url, { waitUntil: 'networkidle' });
    await p.locator('input').first().fill(u); await p.locator('input[type=password]').fill(pw); await p.keyboard.press('Enter'); await p.waitForTimeout(5000);
  }
  await p.goto(spec.base + spec.start, { waitUntil: 'networkidle' }); await p.waitForTimeout(3000);
  let shot = 0; const snap = async () => { const f = `s${String(shot++).padStart(2, '0')}.png`; await p.screenshot({ path: `${OUT}/frames/${f}` }); return f; };
  const now = () => Date.now() / 1000;
  const byText = t => p.getByText(t, { exact: false }).first();
  const glide = async loc => { const x = await loc.boundingBox(); if (x) await p.mouse.move(x.x + x.width / 2, x.y + x.height / 2, { steps: 22 }); };
  const stable = async () => { let last = -1, same = 0; for (let i = 0; i < 30 && same < 3; i++) {
      const y = await p.evaluate(() => scrollY); same = y === last ? same + 1 : 0; last = y; await p.waitForTimeout(120); } };
  const out = [];
  for (const beat of beats.filter(x => spec.beats[x.id])) {
    const s = spec.beats[beat.id], t0 = now(); let before = null;
    for (const a of s.do) {
      if (a.top) { await stable(); await p.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' })); await stable(); if (await p.evaluate(() => scrollY) > 0) { await p.evaluate(() => window.scrollTo(0, 0)); await stable(); } }
      if (a.click) { const btn = p.getByRole('button', { name: a.click }).first(); await btn.scrollIntoViewIfNeeded(); await stable();
        const c = await btn.boundingBox(); before = { img: await snap(), click: { x: (c.x + c.width / 2) * DSF, y: (c.y + c.height / 2) * DSF } };
        await btn.click(); await p.waitForTimeout(450); }
      if (a.open) { const [name, want] = a.open; if (!(await byText(want).isVisible().catch(() => false))) {
          const btn = p.getByRole('button', { name }).first(); await btn.scrollIntoViewIfNeeded(); await glide(btn); await p.waitForTimeout(120); await btn.click(); await p.waitForTimeout(450); } }
      if (a.scroll_to) { await byText(a.scroll_to).evaluate(e => { const r = e.getBoundingClientRect(); window.scrollBy({ top: r.top - innerHeight * 0.4, behavior: 'smooth' }); }); await stable(); }
    }
    await stable();
    // frame the nearest visible block around each target text (border, background or shadow), at most 35% of the screen tall
    const boxes = [], texts = [];
    for (const [k, t] of s.target.entries()) {
      const tag = `tz-${beat.id}-${k}`;
      await byText(t).evaluate((e, tag) => {
        const styled = el => { const c = getComputedStyle(el); return parseFloat(c.borderTopWidth) > 0 || c.boxShadow !== 'none' || !/rgba\(0, 0, 0, 0\)|transparent/.test(c.backgroundColor); };
        let el = e, best = e;
        for (let i = 0; i < 8 && el.parentElement; i++) {
          el = el.parentElement; if (el.getBoundingClientRect().height > innerHeight * 0.35) break;
          best = el; if (styled(el)) break;
        }
        best.setAttribute('data-tz', tag);
      }, tag);
      const bx = await p.locator(`[data-tz="${tag}"]`).boundingBox(); if (bx) boxes.push(bx);
      const tb = await byText(t).boundingBox(); if (tb) texts.push(tb);
    }
    const box = boxes.reduce((u, x) => ({ x0: Math.min(u.x0, x.x), y0: Math.min(u.y0, x.y), x1: Math.max(u.x1, x.x + x.width), y1: Math.max(u.y1, x.y + x.height) }), { x0: 1e9, y0: 1e9, x1: -1e9, y1: -1e9 });
    for (const k of Object.keys(box)) box[k] = Math.round(box[k] * DSF);
    const text = texts.reduce((u, x) => ({ x0: Math.min(u.x0, x.x), y0: Math.min(u.y0, x.y), x1: Math.max(u.x1, x.x + x.width), y1: Math.max(u.y1, x.y + x.height) }), { x0: 1e9, y0: 1e9, x1: -1e9, y1: -1e9 });
    for (const k of Object.keys(text)) text[k] = Math.round(text[k] * DSF);
    const after = await snap();
    const settle = now() - t0;
    out.push({ id: beat.id, settle: +settle.toFixed(2), before, after, box, text, size: [W * DSF, H * DSF] });
  }
  fs.writeFileSync(`${OUT}/tour.json`, JSON.stringify({ beats: out, blocked }, null, 1));
  console.log(JSON.stringify({ beats: out.map(o => [o.id, o.settle, Math.round(o.box.x1 - o.box.x0) + 'x' + Math.round(o.box.y1 - o.box.y0)]), blocked: [...new Set(blocked)] }));
  await b.close();
})();
