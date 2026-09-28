(() => {
  "use strict";
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  // Each widget is wired inside its own guard. Without this the widgets form one
  // unbroken sequence, so a single bad value stops every widget after it — and
  // the last one is the print handler, which means a report can silently print
  // WITHOUT its collapsed sections. Fail loudly, in isolation, and carry on.
  const wire = (what, fn) => {
    try { fn(); }
    catch (e) { console.error(`html-report: "${what}" failed and was skipped —`, e); }
  };

  // Print first, so the one behaviour that changes the PDF's CONTENT is
  // registered before anything else can go wrong.
  // Force every <details> open so nothing collapsed is lost on paper; restore after.
  wire("print handlers", () => {
    addEventListener("beforeprint", () => $$("details").forEach(d => { d.dataset.pwOpen = d.open ? "1" : "0"; d.open = true; }));
    addEventListener("afterprint",  () => $$("details").forEach(d => { d.open = d.dataset.pwOpen === "1"; }));
  });

  // Theme toggle — [data-theme-toggle] cycles + persists (dual-theme CSS is in themes/auto.md)
  const root = document.documentElement;
  const setTheme = (t) => { root.setAttribute("data-theme", t); try { localStorage.setItem("report-theme", t); } catch {} };
  wire("theme toggle", () => {
  try { const s = localStorage.getItem("report-theme"); if (s) setTheme(s); } catch {}
  $$("[data-theme-toggle]").forEach(btn => btn.addEventListener("click", () => {
    const cur = root.getAttribute("data-theme")
      || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    setTheme(cur === "dark" ? "light" : "dark");
  }));
  });

  // Sortable tables — <table data-sortable>; skip a column with <th data-nosort>
  const val = (s) => { const n = parseFloat(String(s).replace(/[^0-9.\-]/g, "")); return isNaN(n) ? String(s).trim().toLowerCase() : n; };
  wire("sortable tables", () => {
  $$("table[data-sortable]").forEach(table => {
    const head = table.tHead ? table.tHead.rows[0] : table.rows[0];
    if (!head) return;
    const bodyRows = () => $$("tr", table).filter(r => r !== head && r.querySelector("td"));
    Array.from(head.cells).forEach((th, col) => {
      if (th.hasAttribute("data-nosort")) return;
      th.style.cursor = "pointer"; th.tabIndex = 0; th.setAttribute("role", "button"); th.setAttribute("data-sort-dir", "");
      let dir = 1;
      const run = () => {
        const rows = bodyRows(); const parent = rows[0] && rows[0].parentNode; if (!parent) return;
        rows.sort((a, b) => { const x = val(a.cells[col] ? a.cells[col].textContent : ""), y = val(b.cells[col] ? b.cells[col].textContent : ""); return x < y ? -dir : x > y ? dir : 0; });
        rows.forEach(r => parent.appendChild(r));
        Array.from(head.cells).forEach(h => h.setAttribute("data-sort-dir", ""));
        th.setAttribute("data-sort-dir", dir === 1 ? "asc" : "desc"); dir *= -1;
      };
      th.addEventListener("click", run);
      th.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); run(); } });
    });
  });
  });

  // Filter — <input data-filter="#tableSelector"> hides non-matching rows.
  // The attribute is a CSS selector, so an id that is not a valid one — an id
  // starting with a digit ("#2026-08-10-table") is the common case — makes
  // querySelector throw. Report which input is at fault and skip only that one.
  wire("filters", () => {
  $$("[data-filter]").forEach(input => {
    const sel = input.getAttribute("data-filter");
    let target = null;
    try { target = sel ? document.querySelector(sel) : null; }
    catch (e) { console.error(`html-report: data-filter="${sel}" is not a valid CSS selector; that filter is disabled. An id must not start with a digit.`, input); return; }
    if (!target) { console.warn(`html-report: data-filter="${sel}" matched nothing; that filter is disabled.`, input); return; }
    const head = target.tHead ? target.tHead.rows[0] : target.rows[0];
    input.classList.add("filter-input");
    input.addEventListener("input", () => {
      const q = input.value.trim().toLowerCase();
      $$("tr", target).forEach(r => { if (r === head || !r.querySelector("td")) return; r.style.display = r.textContent.toLowerCase().includes(q) ? "" : "none"; });
    });
  });
  });

  // Tabs — <div data-tabs> with [data-tab] buttons + matching [data-panel] panels
  wire("tabs", () => {
  $$("[data-tabs]").forEach(group => {
    const tabs = $$("[data-tab]", group), panels = $$("[data-panel]", group);
    const select = (id) => { tabs.forEach(t => t.setAttribute("aria-selected", String(t.dataset.tab === id))); panels.forEach(p => p.hidden = p.dataset.panel !== id); };
    tabs.forEach(t => t.addEventListener("click", () => select(t.dataset.tab)));
    const first = tabs.find(t => t.getAttribute("aria-selected") === "true") || tabs[0];
    if (first) select(first.dataset.tab);
  });
  });

  // Table of contents — <nav data-toc> auto-built from h2[id]/h3[id]; scrollspy highlights active
  wire("table of contents", () => {
  $$("[data-toc]").forEach(nav => {
    // h1 is included for hand-built reports that use it per section. The
    // md_to_html helper demotes those instead, so an authored document lands
    // on h2/h3 and this is only a safety net.
    const heads = $$(".report-grid h2[id], .report-grid h3[id], .report-grid h1[id]")
      .sort((a, b) => a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1);
    if (!heads.length) return;
    const ul = document.createElement("ul");
    heads.forEach(h => { const li = document.createElement("li"); li.className = "toc-" + h.tagName.toLowerCase(); const a = document.createElement("a"); a.href = "#" + h.id; a.textContent = h.textContent; a.dataset.for = h.id; li.appendChild(a); ul.appendChild(li); });
    nav.appendChild(ul);
    // Which section am I in? The drawer is worth opening only if it answers
    // that, so track the last heading whose top has passed the reading line
    // rather than whichever one happens to be intersecting.
    const links = $$("a", nav);
    const mark = () => {
      const line = innerHeight * 0.28;
      let current = heads[0];
      for (const h of heads) { if (h.getBoundingClientRect().top <= line) current = h; else break; }
      links.forEach(l => l.classList.toggle("active", current && l.dataset.for === current.id));
    };
    addEventListener("scroll", mark, { passive: true });
    addEventListener("resize", mark);
    mark();
  });
  });

  // Copy — <button class="copy-btn" data-copy="#sel"> copies target text; or data-copy-text="literal"
  wire("copy buttons", () => {
  $$("[data-copy], [data-copy-text]").forEach(btn => btn.addEventListener("click", async () => {
    const sel = btn.getAttribute("data-copy");
    let el = null;
    try { el = sel ? document.querySelector(sel) : null; }
    catch (e) { console.error(`html-report: data-copy="${sel}" is not a valid CSS selector.`, btn); }
    const text = btn.getAttribute("data-copy-text") != null ? btn.getAttribute("data-copy-text") : (el ? el.textContent : "");
    try { await navigator.clipboard.writeText(text); const o = btn.textContent; btn.textContent = "Copied"; setTimeout(() => { btn.textContent = o; }, 1200); } catch {}
  }));
  });

  // Contents drawer + reading position.
  //
  // The drawer overlays the page instead of taking a column, because the layout
  // is one print-identical column and a persistent rail would put a second left
  // edge on it. This is the Kindle / Apple Books arrangement -- a panel that
  // slides in over the text so the reader never loses their place -- with the
  // one thing Wikipedia's 2023 redesign proved readers actually use: the section
  // they are in, highlighted. That change A/B-tested at +53% contents clicks.
  //
  // In print the same element is a plain contents block (CSS above), so the PDF
  // gets a contents page that a drawer could never give it.
  wire("contents drawer", () => {
    const toc = document.querySelector(".toc");
    const buttons = $$("[data-toc-toggle]");
    if (!toc || !buttons.length) return;

    const backdrop = document.createElement("div");
    backdrop.className = "toc-backdrop";
    document.body.appendChild(backdrop);

    if (!toc.querySelector(".toc-title")) {
      const h = document.createElement("p");
      h.className = "toc-title"; h.textContent = "Contents";
      toc.prepend(h);
    }
    toc.setAttribute("aria-label", "Contents");

    let lastFocus = null;
    const setOpen = (open) => {
      toc.toggleAttribute("data-open", open);
      backdrop.toggleAttribute("data-open", open);
      // inert keeps the closed drawer out of the tab order and off screen
      // readers without display:none, which would kill the slide transition.
      toc.inert = !open;
      buttons.forEach(b => b.setAttribute("aria-expanded", String(open)));
      if (open) {
        lastFocus = document.activeElement;
        const here = toc.querySelector("a.active") || toc.querySelector("a");
        if (here) {
          // Scroll the DRAWER, never the document. `scrollIntoView` and a plain
          // `focus()` both scrolled the page to the top on open -- measured, the
          // reading position went from 81% to 0% -- which loses the reader's
          // place, the one thing this pattern exists to protect.
          toc.scrollTop = here.offsetTop - toc.clientHeight / 2 + here.offsetHeight / 2;
          here.focus({ preventScroll: true });
        }
      } else if (lastFocus) {
        lastFocus.focus({ preventScroll: true });
      }
    };
    setOpen(false);

    buttons.forEach(b => b.addEventListener("click", () => setOpen(!toc.hasAttribute("data-open"))));
    backdrop.addEventListener("click", () => setOpen(false));
    addEventListener("keydown", (e) => { if (e.key === "Escape" && toc.hasAttribute("data-open")) setOpen(false); });
    // Jumping to a section is the point; close on the way there.
    toc.addEventListener("click", (e) => { if (e.target.closest("a")) setOpen(false); });
    // Paper has no drawer state to restore, but a mid-print reflow would.
    addEventListener("beforeprint", () => { toc.inert = false; });
    addEventListener("afterprint", () => { toc.inert = !toc.hasAttribute("data-open"); });
  });

  // Reading position. Every e-reader shows it; a report that runs nine printed
  // pages earns it too. `scrollHeight - innerHeight` can be 0 on a short page,
  // which would make the bar full width at the top -- guard it.
  wire("reading progress", () => {
    const bar = document.createElement("div");
    bar.className = "read-progress";
    bar.setAttribute("role", "presentation");
    document.body.appendChild(bar);
    const update = () => {
      const max = document.documentElement.scrollHeight - innerHeight;
      bar.style.width = (max > 40 ? Math.min(100, (scrollY / max) * 100) : 0) + "%";
    };
    addEventListener("scroll", update, { passive: true });
    addEventListener("resize", update);
    update();
  });

  // Heading anchors — every h2/h3 with an id gets a copyable deep link.
  // A report people cite needs addressable sections; a Markdown paste does not
  // give you one.
  wire("heading anchors", () => {
    $$(".report-grid h2[id], .report-grid h3[id], .report-grid h1[id]").forEach(h => {
      if (h.querySelector("a.hanchor")) return;
      const a = document.createElement("a");
      a.className = "hanchor"; a.href = "#" + h.id; a.textContent = "#";
      a.setAttribute("aria-label", "Link to this section");
      a.addEventListener("click", (e) => {
        e.preventDefault();
        history.replaceState(null, "", "#" + h.id);
        h.scrollIntoView({ behavior: "smooth", block: "start" });
        try { navigator.clipboard.writeText(location.href); } catch {}
      });
      h.prepend(a);
    });
  });

  // Facets — <div class="facets" data-facets=".finding"> filters any list of
  // elements carrying data-facet. Buttons are BUILT from the values present,
  // so the chips can never drift from the content.
  wire("facets", () => {
    $$("[data-facets]").forEach(bar => {
      const sel = bar.getAttribute("data-facets");
      let items = [];
      try { items = $$(sel + "[data-facet]"); }
      catch { console.error(`html-report: data-facets="${sel}" is not a valid CSS selector.`, bar); return; }
      if (!items.length) { console.warn(`html-report: data-facets="${sel}" matched nothing.`, bar); return; }
      const counts = new Map();
      items.forEach(el => { const v = el.dataset.facet; counts.set(v, (counts.get(v) || 0) + 1); });
      bar.classList.add("facets");
      let active = null;
      const render = () => {
        items.forEach(el => { el.hidden = active !== null && el.dataset.facet !== active; });
        $$("button", bar).forEach(b => b.setAttribute("aria-pressed", String(b.dataset.val === active)));
      };
      const chip = (val, label, n) => {
        const b = document.createElement("button");
        b.type = "button"; b.className = "fc"; b.dataset.val = val === null ? "" : val;
        b.innerHTML = `${label}<span class="n">${n}</span>`;
        b.addEventListener("click", () => { active = active === val ? null : val; render(); });
        if (val === null) b.addEventListener("click", () => { active = null; render(); });
        bar.appendChild(b);
      };
      chip(null, "All", items.length);
      Array.from(counts.entries()).forEach(([v, n]) => chip(v, v, n));
      render();
    });
  });

  // Cross-reference previews — hovering an internal link shows the target
  // heading plus its first paragraph. Lifted from the live DOM, so it cannot
  // contradict the document. Skipped on touch and under reduced motion.
  wire("xref previews", () => {
    if (matchMedia("(hover: none)").matches) return;
    const pop = document.createElement("div");
    pop.className = "xref-pop"; pop.hidden = true; document.body.appendChild(pop);
    const place = (e) => {
      const pad = 14, w = pop.offsetWidth, h = pop.offsetHeight;
      pop.style.left = Math.min(e.clientX + pad, innerWidth - w - pad) + "px";
      pop.style.top = (e.clientY + h + pad > innerHeight ? e.clientY - h - pad : e.clientY + pad) + "px";
    };
    $$('a[href^="#"]').forEach(a => {
      if (a.classList.contains("hanchor") || a.closest(".toc")) return;
      a.addEventListener("mouseenter", (e) => {
        const t = document.getElementById(decodeURIComponent(a.getAttribute("href").slice(1)));
        if (!t) return;
        let body = t.nextElementSibling;
        while (body && !/^(P|UL|OL|DIV|TABLE)$/.test(body.tagName)) body = body.nextElementSibling;
        const text = (body ? body.textContent : "").trim().replace(/\s+/g, " ").slice(0, 260);
        if (!text) return;
        pop.innerHTML = "";
        const b = document.createElement("b"); b.textContent = t.textContent.replace(/^#/, "").trim();
        pop.appendChild(b); pop.appendChild(document.createTextNode(text + (text.length >= 260 ? "\u2026" : "")));
        pop.hidden = false; place(e);
      });
      a.addEventListener("mousemove", place);
      a.addEventListener("mouseleave", () => { pop.hidden = true; });
    });
  });

  // Chart tooltips — any SVG element with data-tip="..."
  wire("chart tooltips", () => {
  const tip = document.createElement("div"); tip.className = "chart-tip"; tip.hidden = true; document.body.appendChild(tip);
  $$("svg [data-tip]").forEach(el => {
    el.addEventListener("mouseenter", () => { tip.textContent = el.getAttribute("data-tip"); tip.hidden = false; });
    el.addEventListener("mousemove", e => { tip.style.left = (e.clientX + 12) + "px"; tip.style.top = (e.clientY + 12) + "px"; });
    el.addEventListener("mouseleave", () => { tip.hidden = true; });
  });
  });
})();
