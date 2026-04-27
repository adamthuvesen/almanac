  const BUNDLE = JSON.parse(document.getElementById("almanac-bundle").textContent);
  window.BUNDLE = BUNDLE;

  // Palette
  const C = {
    cream: "#F4EDE0", ink: "#1C1612", rust: "#A94F2E",
    sage:  "#5B6A47", ochre: "#C9A24A", plum: "#4A2E3B",
  };

  // Utilities
  const fmt = new Intl.NumberFormat("en-US");
  const escapeHtml = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));

  const fmtDate = (iso) => {
    if (!iso) return "";
    try {
      const d = new Date(iso);
      return d.toLocaleDateString("en-US", {
        year: "numeric", month: "long", day: "numeric",
      });
    } catch { return iso; }
  };

  const DOW = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];
  const VERB_COLOR = {
    feat: C.sage, fix: C.rust, chore: C.ochre, docs: "#7B9EC8",
    refactor: C.rust, test: C.cream, style: C.sage, perf: C.ochre,
    build: "#B896C8", ci: C.sage, revert: C.rust,
    unclear: "rgba(244, 237, 224, 0.30)",
  };
  const LANG_PALETTE = [C.rust, C.sage, C.ochre, C.plum, C.ink];
  const LANG_PALETTE_DARK = [C.rust, C.sage, C.ochre, "#5B9E6A", C.cream];

  const THEMES = {
    cover:          { bg: "#1D3327", fg: C.cream, accent: "#7EC8A0" },
    "first-commit": { bg: "#12162B", fg: C.cream, accent: C.ochre   },
    numbers:        { bg: "#2B1608", fg: C.cream, accent: C.cream   },
    heatmap:        { bg: "#0D1F2D", fg: C.cream, accent: "#5B8FA0" },
    cadence:        { bg: "#221900", fg: C.cream, accent: C.ochre   },
    "top-files":    { bg: "#1A1A1E", fg: C.cream, accent: C.rust    },
    languages:      { bg: "#0F1E14", fg: C.cream, accent: "#5B9E6A" },
    verbs:          { bg: "#2B0A0A", fg: C.cream, accent: "#CF6B5E" },
    authors:        { bg: "#1C0E26", fg: C.cream, accent: "#9B6FAB" },
    closer:         { bg: "#1D3327", fg: C.cream, accent: "#7EC8A0" },
  };

  // Slide builder helpers
  const root = document.getElementById("root");
  const make = (tag, attrs = {}, html = "") => {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === "class") el.className = v;
      else if (k === "style") el.style.cssText = v;
      else el.setAttribute(k, v);
    }
    if (html) el.innerHTML = html;
    return el;
  };
  const slide = (id, inner, theme = null) => {
    const s = make("section", { class: "slide", id });
    s.innerHTML = inner;
    if (theme) {
      s.style.setProperty("--slide-bg",     theme.bg);
      s.style.setProperty("--slide-fg",     theme.fg ?? C.cream);
      s.style.setProperty("--slide-accent", theme.accent);
    }
    root.appendChild(s);
    return s;
  };

  function letterSpans(text) {
    return [...String(text)].map((ch) => {
      if (ch === " ") return `<span class="ch">&nbsp;</span>`;
      return `<span class="ch" style="display:inline-block">${escapeHtml(ch)}</span>`;
    }).join("");
  }

  // Data-backed micro-copy: renders a caption only when the slot is
  // present and non-empty. Returns "" otherwise so empty templates
  // don't emit stray <p> elements.
  const microcopy = BUNDLE.microcopy || {};
  const caption = (slot, { subtle = false } = {}) => {
    const text = microcopy[slot];
    if (!text) return "";
    const cls = subtle ? "slide-caption subtle" : "slide-caption";
    return `<p class="${cls}">${escapeHtml(text)}</p>`;
  };

  // ── Cover ──────────────────────────────────────────────────────────────
  const coverCount = BUNDLE.commit_count ?? 0;
  slide("cover", `
    <div class="eyebrow ui">Almanac</div>
    <div class="display cover-title">${letterSpans(BUNDLE.repo?.name || "repo")}</div>
    ${caption("cover_intro")}
    <div class="cover-meta">
      <div><div class="label">Window</div><div class="value mono">${escapeHtml(BUNDLE.window?.label || "")}</div></div>
      <div><div class="label">Commits</div><div class="value mono">${fmt.format(coverCount)}</div></div>
      <div><div class="label">HEAD</div><div class="value mono">${escapeHtml((BUNDLE.repo?.head_sha || "").slice(0,7))}</div></div>
    </div>
    <div class="cover-tag prose">A year in commits — scroll to begin.</div>
  `, THEMES.cover);

  // ── First Commit ───────────────────────────────────────────────────────
  if (BUNDLE.first_commit) {
    const fc = BUNDLE.first_commit;
    slide("first-commit", `
      <div class="narrative">
        <div class="eyebrow ui">First Commit</div>
        <div class="caption prose">The year began here.</div>
        <div class="subject">${escapeHtml(fc.subject || "")}</div>
        <div class="meta">
          <div><span style="opacity:.6">author</span> ${escapeHtml(fc.author || "")}</div>
          <div><span style="opacity:.6">date</span> ${escapeHtml(fmtDate(fc.ts))}</div>
          <div><span style="opacity:.6">sha</span> ${escapeHtml((fc.sha || "").slice(0,7))}</div>
        </div>
      </div>
    `, THEMES["first-commit"]);
  }

  // ── Year in Numbers ────────────────────────────────────────────────────
  const stats = [
    ["Commits",         BUNDLE.commit_count ?? 0],
    ["Lines added",     BUNDLE.lines_added ?? 0],
    ["Lines removed",   BUNDLE.lines_removed ?? 0],
    ["Longest streak",  BUNDLE.longest_streak_days ?? 0],
    ["Longest gap",     BUNDLE.longest_gap_days ?? 0],
    ["Biggest commit",  BUNDLE.biggest_commit?.delta ?? 0],
  ];
  const bc = BUNDLE.biggest_commit;
  slide("numbers", `
    <div class="eyebrow ui">Year in Numbers</div>
    <h2 class="section display">By the numbers.</h2>
    ${caption("numbers_caption")}
    <div class="grid6">
      ${stats.map(([label, value]) => {
    const isBig = label === "Biggest commit" && bc;
    const attrs = isBig
      ? ` class="stat stat-receipt" data-sha="${escapeHtml(bc.sha || "")}" data-date="${escapeHtml(bc.ts || "")}" data-subject="${escapeHtml(bc.subject || "")}"`
      : ` class="stat"`;
    return `<div${attrs}>
          <div class="figure" data-target="${value}">0</div>
          <div class="label">${escapeHtml(label)}</div>
        </div>`;
  }).join("")}
    </div>
  `, THEMES.numbers);

  // ── Calendar Heatmap ───────────────────────────────────────────────────
  if (Array.isArray(BUNDLE.commits_per_day) && BUNDLE.commits_per_day.length > 0) {
    slide("heatmap", `
      <div class="eyebrow ui">Calendar Heatmap</div>
      <h2 class="section display">Day by day.</h2>
      <div class="heatmap-wrap" id="heatmap-target"></div>
      <div class="footnote ui">One cell per day. Cream = no commits. Rust = busiest.</div>
    `, THEMES.heatmap);
  }

  // ── Cadence ────────────────────────────────────────────────────────────
  slide("cadence", `
    <div class="eyebrow ui">Commit Cadence</div>
    <h2 class="section display">When you ship.</h2>
    ${caption("cadence_caption")}
    ${caption("comeback_caption", { subtle: true }) || caption("quiet_caption", { subtle: true })}
    <div class="charts-row">
      <div>
        <div class="ui" style="font-size:13px;color:var(--plum);text-transform:uppercase;letter-spacing:.14em;margin-bottom:.6rem">By weekday</div>
        <div id="dow-chart" class="chart-wrap"></div>
      </div>
      <div>
        <div class="ui" style="font-size:13px;color:var(--plum);text-transform:uppercase;letter-spacing:.14em;margin-bottom:.6rem">By hour</div>
        <div id="hour-chart" class="chart-wrap"></div>
      </div>
    </div>
  `, THEMES.cadence);

  // ── Top Files ──────────────────────────────────────────────────────────
  const filesRaw = (BUNDLE.files_by_churn || []).slice(0, 15);
  if (filesRaw.length > 0) {
    const maxEdits = Math.max(...filesRaw.map((f) => f.edits || 0), 1);
    slide("top-files", `
      <div class="eyebrow ui">Top Files</div>
      <h2 class="section display">Most touched.</h2>
      ${caption("top_files_caption")}
      <div class="file-bars">
        ${filesRaw.map((f) => `
          <div class="row has-bar">
            <div class="path" title="${escapeHtml(f.path)}">${escapeHtml(f.path)}</div>
            <div class="bar-track"><div class="bar" data-pct="${(f.edits / maxEdits) * 100}" data-subjects="${escapeHtml(JSON.stringify(f.subjects ?? []))}"></div></div>
            <div class="edits">${fmt.format(f.edits)}</div>
          </div>
        `).join("")}
      </div>
    `, THEMES["top-files"]);
  }

  // ── Languages ──────────────────────────────────────────────────────────
  const langs = (BUNDLE.languages || []).filter((l) => (l.lines ?? 0) > 0);
  if (langs.length > 0) {
    const total = langs.reduce((a, l) => a + l.lines, 0);
    const top = langs.slice(0, 8);
    slide("languages", `
      <div class="eyebrow ui">Languages</div>
      <h2 class="section display">In which tongues.</h2>
      <div class="stack-bar" id="lang-bar">
        ${top.map((l, i) => `
          <div data-target-pct="${(l.lines / total) * 100}" style="background:${LANG_PALETTE_DARK[i % LANG_PALETTE_DARK.length]}"></div>
        `).join("")}
      </div>
      <div class="stack-legend">
        ${top.map((l, i) => `
          <span><span class="swatch" style="background:${LANG_PALETTE_DARK[i % LANG_PALETTE_DARK.length]}"></span>
          ${escapeHtml(l.ext || "(none)")}<span class="pct">${(l.lines / total * 100).toFixed(1)}%</span></span>
        `).join("")}
      </div>
      <div class="ranked">
        ${langs.slice(0, 10).map((l, i) => `
          <div class="row">
            <div class="rank">#${String(i + 1).padStart(2, "0")}</div>
            <div class="name">${escapeHtml(l.ext || "(none)")}</div>
            <div class="num">${fmt.format(l.lines)}</div>
            <div class="num">${(l.lines / total * 100).toFixed(1)}%</div>
          </div>
        `).join("")}
      </div>
    `, THEMES.languages);
  }

  // ── Verbs ──────────────────────────────────────────────────────────────
  const verbsObj = BUNDLE.verbs || {};
  const verbsArr = Object.entries(verbsObj)
    .filter(([_, n]) => n > 0)
    .map(([verb, n]) => ({ verb, n }))
    .sort((a, b) => b.n - a.n);
  if (verbsArr.length > 0) {
    const totalV = verbsArr.reduce((a, v) => a + v.n, 0);
    const top1 = verbsArr[0]?.verb;
    const top2 = verbsArr[1]?.verb;
    let tagline;
    if (top1 && top2) {
      tagline = `Mostly <code>${escapeHtml(top1)}</code>-ing, a little <code>${escapeHtml(top2)}</code>-ing.`;
    } else if (top1) {
      tagline = `Mostly <code>${escapeHtml(top1)}</code>-ing.`;
    } else {
      tagline = "A quiet year.";
    }
    slide("verbs", `
      <div class="eyebrow ui">Commit Verbs</div>
      <h2 class="section display">What you did.</h2>
      ${caption("verbs_caption")}
      <div class="stack-bar" id="verb-bar">
        ${verbsArr.map((v) => `
          <div data-target-pct="${(v.n / totalV) * 100}" style="background:${VERB_COLOR[v.verb] || C.ink}"></div>
        `).join("")}
      </div>
      <div class="stack-legend">
        ${verbsArr.map((v) => `
          <span><span class="swatch" style="background:${VERB_COLOR[v.verb] || C.ink}"></span>
          ${escapeHtml(v.verb)}<span class="pct">${(v.n / totalV * 100).toFixed(1)}%</span></span>
        `).join("")}
      </div>
      <div class="tagline">${tagline}</div>
    `, THEMES.verbs);
  }

  // ── Authors ────────────────────────────────────────────────────────────
  const authors = BUNDLE.authors || [];
  if (authors.length > 0) {
    const top10 = authors.slice(0, 10);
    const more = Math.max(0, authors.length - 10);
    const authorsSlide = slide("authors", `
      <div class="eyebrow ui">Authors</div>
      <h2 class="section display">Whose hands.</h2>
      <div class="authors-list">
        ${top10.map((a, i) => {
          const initials = (a.name || "?").split(/\s+/).map(s => s[0] || "").join("").slice(0,2).toUpperCase();
          const hash = a.avatar_hash || "";
          return `
            <div class="author-row">
              <div class="rank mono">#${String(i + 1).padStart(2, "0")}</div>
              <div class="avatar-slot" data-hash="${escapeHtml(hash)}" data-initials="${escapeHtml(initials)}"></div>
              <div class="name prose" style="font-size:24px">${escapeHtml(a.name || "Unknown")}</div>
              <div class="num commits mono" style="text-align:right">${fmt.format(a.commits)} commits</div>
              <div class="num added mono" style="text-align:right">+${fmt.format(a.lines_added)}</div>
              <div class="num removed mono" style="text-align:right">−${fmt.format(a.lines_removed)}</div>
            </div>
          `;
        }).join("")}
      </div>
      ${more > 0 ? `<div class="footnote ui">…and ${more} more.</div>` : ""}
    `, THEMES.authors);
    // Hydrate avatar slots with DOM APIs (no inline event handlers, no
    // user data inside HTML attributes that would be parsed as JS).
    authorsSlide.querySelectorAll(".avatar-slot").forEach((slot) => {
      const hash = slot.dataset.hash || "";
      const initials = slot.dataset.initials || "";
      const initialsDiv = document.createElement("div");
      initialsDiv.className = "avatar";
      initialsDiv.textContent = initials;
      if (hash) {
        const img = document.createElement("img");
        img.className = "avatar";
        img.alt = "";
        img.src = `https://www.gravatar.com/avatar/${hash}?d=404&s=96`;
        img.addEventListener("error", () => img.replaceWith(initialsDiv));
        slot.replaceWith(img);
      } else {
        slot.replaceWith(initialsDiv);
      }
    });
  }

  // ── Closer ─────────────────────────────────────────────────────────────
  slide("closer", `
    <div class="eyebrow ui">Fin</div>
    <div class="display cover-title">See you next year.</div>
    ${caption("closer_signoff")}
    <div class="cover-tag prose">Until then — keep shipping.</div>
    <div class="cover-meta">
      <div><div class="label">Window</div><div class="value mono">${escapeHtml(BUNDLE.window?.label || "")}</div></div>
      <div><div class="label">HEAD</div><div class="value mono">${escapeHtml((BUNDLE.repo?.head_sha || "").slice(0,7))}</div></div>
    </div>
  `, THEMES.closer);

  // ── Native chart rendering ─────────────────────────────────────────────
  const SVG_NS = "http://www.w3.org/2000/svg";
  const svgEl = (tag, attrs = {}) => {
    const el = document.createElementNS(SVG_NS, tag);
    for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
    return el;
  };
  const clearNode = (node) => { while (node.firstChild) node.removeChild(node.firstChild); };
  const hexToRgb = (hex) => {
    const raw = hex.replace("#", "");
    const n = parseInt(raw.length === 3 ? raw.split("").map((c) => c + c).join("") : raw, 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  };
  const mix = (a, b, t) => {
    const ar = hexToRgb(a), br = hexToRgb(b);
    const ch = ar.map((v, i) => Math.round(v + (br[i] - v) * t));
    return `rgb(${ch[0]}, ${ch[1]}, ${ch[2]})`;
  };
  const rampColor = (t) => {
    if (t <= 0) return C.cream;
    if (t < 0.45) return mix(C.cream, C.sage, t / 0.45);
    if (t < 0.75) return mix(C.sage, C.ochre, (t - 0.45) / 0.30);
    return mix(C.ochre, C.rust, (t - 0.75) / 0.25);
  };
  const parseLocalDate = (s) => new Date(`${s}T00:00:00`);
  const dayOfWeekMon0 = (d) => (d.getDay() + 6) % 7;
  const startOfWeek = (d) => {
    const out = new Date(d);
    out.setDate(out.getDate() - dayOfWeekMon0(out));
    out.setHours(0, 0, 0, 0);
    return out;
  };
  const daysBetween = (a, b) => Math.round((b - a) / 86400000);

  const almanacReceiptDtf = new Intl.DateTimeFormat("en-US", {
    weekday: "short", month: "short", day: "numeric", year: "numeric",
  });

  let almanacOpenReceiptRow = null;
  let almanacBiggestReceiptPopover = null;

  function almanacCloseTopFileReceiptsPanel() {
    if (!almanacOpenReceiptRow) return;
    almanacOpenReceiptRow.querySelector(".receipts-panel")?.remove();
    almanacOpenReceiptRow = null;
  }

  function almanacCloseBiggestReceiptPopover() {
    almanacBiggestReceiptPopover?.remove();
    almanacBiggestReceiptPopover = null;
  }

  function almanacCloseAllReceiptOverlays() {
    almanacCloseTopFileReceiptsPanel();
    almanacCloseBiggestReceiptPopover();
  }

  /**
   * Binds one shared heatmap cell tooltip (#heatmap-tooltip). Invoked
   * after each heatmap render (incl. resize). Marker: almanac-heatmap-receipt
   */
  function almanacBindHeatmapReceiptTooltip(svg) {
    const tip = document.getElementById("heatmap-tooltip");
    if (!tip || !svg) return;
    svg.querySelectorAll("rect.hm-cell[data-date]").forEach((rect) => {
      const show = (e) => {
        const ds = rect.getAttribute("data-date");
        if (!ds) return;
        const n = parseInt(rect.getAttribute("data-count") || "0", 10);
        const d = parseLocalDate(ds);
        const when = almanacReceiptDtf.format(d);
        const c = Number.isNaN(n) ? 0 : n;
        const label = c === 1 ? "1 commit" : `${c} commits`;
        tip.textContent = `${when} · ${label}`;
        tip.style.display = "block";
        requestAnimationFrame(() => almanacPositionReceiptTooltip(tip, e));
      };
      const move = (e) => almanacPositionReceiptTooltip(tip, e);
      const hide = () => { tip.style.display = "none"; };
      rect.addEventListener("mouseenter", show);
      rect.addEventListener("mousemove", move);
      rect.addEventListener("mouseleave", hide);
    });
  }

  function almanacPositionReceiptTooltip(el, e) {
    if (!e || e.clientX == null) return;
    const pad = 12;
    el.style.position = "fixed";
    const w = el.offsetWidth || 180;
    const h = el.offsetHeight || 24;
    const x = e.clientX + pad;
    const y = e.clientY + pad;
    const maxX = window.innerWidth - w - 8;
    const maxY = window.innerHeight - h - 8;
    el.style.left = `${Math.max(8, Math.min(x, maxX))}px`;
    el.style.top = `${Math.max(8, Math.min(y, maxY))}px`;
  }

  /**
   * One-time: top-file subjects panel, biggest-commit popover, Escape, outside-click.
   * Markers: receipts-panel, almanac-biggest-receipt-popover
   */
  function almanacSetupInspectableReceipts() {
    if (window.__almanacReceiptsWired) return;
    window.__almanacReceiptsWired = true;

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") almanacCloseAllReceiptOverlays();
    });

    const top = document.getElementById("top-files");
    if (top) {
      top.addEventListener("click", (e) => {
        const bar = e.target instanceof Element ? e.target.closest(".bar[data-subjects]") : null;
        if (!bar) return;
        e.stopPropagation();
        almanacCloseBiggestReceiptPopover();
        const row = bar.closest?.(".row.has-bar");
        if (!row) return;
        if (almanacOpenReceiptRow === row) {
          almanacCloseTopFileReceiptsPanel();
          return;
        }
        almanacCloseTopFileReceiptsPanel();
        almanacOpenReceiptRow = row;
        let subjects = [];
        try {
          const raw = bar.getAttribute("data-subjects");
          subjects = raw ? JSON.parse(raw) : [];
        } catch { subjects = []; }
        if (!Array.isArray(subjects)) subjects = [];
        const li = (subjects.length
          ? subjects.map((s) => `<li>${escapeHtml(s)}</li>`).join("")
          : '<li class="receipts-empty">No commit subjects recorded</li>');
        const panel = make("ul", { class: "receipts-panel" });
        panel.innerHTML = li;
        row.appendChild(panel);
        requestAnimationFrame(() => panel.classList.add("receipts-panel-open"));
      });
    }

    const numBig = document.querySelector("#numbers .stat[data-sha]");
    if (numBig) {
      numBig.addEventListener("click", (e) => {
        e.stopPropagation();
        if (almanacBiggestReceiptPopover) {
          almanacCloseBiggestReceiptPopover();
          return;
        }
        almanacCloseTopFileReceiptsPanel();
        const sha = (numBig.getAttribute("data-sha") || "").slice(0, 7);
        const iso = numBig.getAttribute("data-date") || "";
        const subj = numBig.getAttribute("data-subject") || "";
        const pop = make("div", { class: "almanac-biggest-receipt-popover" });
        pop.innerHTML = `
          <div class="receipt-pop-sha mono">${escapeHtml(sha)}</div>
          <div class="receipt-pop-when">${escapeHtml(fmtDate(iso))}</div>
          <div class="receipt-pop-subj">${escapeHtml(subj)}</div>
        `;
        const r = numBig.getBoundingClientRect();
        pop.style.left = `${r.left}px`;
        pop.style.top = `${r.bottom + 6}px`;
        document.body.appendChild(pop);
        almanacBiggestReceiptPopover = pop;
      });
      document.addEventListener("click", (e) => {
        if (!almanacBiggestReceiptPopover) return;
        if (e.target === numBig || numBig.contains(e.target)) return;
        if (almanacBiggestReceiptPopover.contains(e.target)) return;
        almanacCloseBiggestReceiptPopover();
      });
    }
  }

  function renderHeatmap() {
    const target = document.getElementById("heatmap-target");
    if (!target) return;
    clearNode(target);
    const data = (BUNDLE.commits_per_day || []).map((d) => {
      const dt = parseLocalDate(d.date);
      return {
        date: dt,
        dateStr: d.date,
        dow: dayOfWeekMon0(dt),
        count: d.count || 0,
      };
    });
    if (!data.length) return;
    const start = startOfWeek(data[0].date);
    const last = data[data.length - 1].date;
    const weekCount = Math.floor(daysBetween(start, last) / 7) + 1;
    const cell = 18;
    const left = 42;
    const top = 4;
    const width = left + weekCount * cell + 8;
    const height = top + DOW.length * cell + 28;
    const maxCount = Math.max(...data.map((d) => d.count), 1);
    const svg = svgEl("svg", {
      class: "native-chart",
      viewBox: `0 0 ${width} ${height}`,
      role: "img",
      "aria-label": "Calendar heatmap",
    });
    DOW.forEach((label, i) => {
      const text = svgEl("text", { x: 0, y: top + i * cell + 13 });
      text.textContent = label;
      svg.append(text);
    });
    data.forEach((d) => {
      const week = Math.floor(daysBetween(start, d.date) / 7);
      const ratio = maxCount ? d.count / maxCount : 0;
      const rect = svgEl("rect", {
        x: left + week * cell,
        y: top + d.dow * cell,
        width: cell - 3,
        height: cell - 3,
        rx: 2,
        fill: rampColor(ratio),
        opacity: d.count ? "1" : "0.35",
        "data-date": d.dateStr,
        "data-count": String(d.count),
        class: "hm-cell",
      });
      const title = svgEl("title");
      title.textContent = `${d.date.toISOString().slice(0, 10)}: ${d.count} commits`;
      rect.append(title);
      svg.append(rect);
    });
    target.append(svg);
    almanacBindHeatmapReceiptTooltip(svg);
  }

  function renderBar(targetId, data, labels, fill = C.rust, labelColor = C.ink) {
    const target = document.getElementById(targetId);
    if (!target) return;
    clearNode(target);
    const width = Math.min(700, target.clientWidth || 600);
    const height = 280;
    const margin = { top: 16, right: 12, bottom: 34, left: 42 };
    const innerW = width - margin.left - margin.right;
    const innerH = height - margin.top - margin.bottom;
    const maxVal = Math.max(...data, 1);
    const barW = innerW / Math.max(data.length, 1);
    const svg = svgEl("svg", {
      class: "native-chart",
      viewBox: `0 0 ${width} ${height}`,
      role: "img",
      "aria-label": targetId,
      style: `color:${labelColor}`,
    });
    for (let i = 0; i <= 4; i++) {
      const y = margin.top + innerH - (innerH * i / 4);
      svg.append(svgEl("line", {
        class: "grid-line",
        x1: margin.left,
        x2: width - margin.right,
        y1: y,
        y2: y,
      }));
    }
    data.forEach((value, i) => {
      const h = maxVal ? (value / maxVal) * innerH : 0;
      const x = margin.left + i * barW + Math.max(2, barW * 0.12);
      const y = margin.top + innerH - h;
      svg.append(svgEl("rect", {
        x,
        y,
        width: Math.max(2, barW * 0.76),
        height: h,
        rx: 2,
        fill,
      }));
      const text = svgEl("text", {
        x: margin.left + i * barW + barW / 2,
        y: height - 10,
        "text-anchor": "middle",
      });
      text.textContent = labels[i] ?? "";
      svg.append(text);
    });
    target.append(svg);
  }

  // ── Animations ─────────────────────────────────────────────────────────
  function animateCounters() {
    document.querySelectorAll(".stat .figure").forEach((el) => {
      const target = parseFloat(el.dataset.target) || 0;
      const start = performance.now();
      const duration = 900;
      const tick = (now) => {
        const t = Math.min(1, (now - start) / duration);
        const eased = 1 - Math.pow(1 - t, 3);
        el.textContent = fmt.format(Math.round(target * eased));
        if (t < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
  }

  function fillBars(animated = true) {
    ["lang-bar", "verb-bar"].forEach((id) => {
      const bar = document.getElementById(id);
      if (!bar) return;
      [...bar.children].forEach((seg, i) => {
        const pct = parseFloat(seg.dataset.targetPct) || 0;
        const delay = animated ? i * 80 : 0;
        setTimeout(() => { seg.style.width = pct + "%"; }, delay);
      });
    });
    document.querySelectorAll("#top-files .bar").forEach((el, i) => {
      const pct = parseFloat(el.dataset.pct) || 0;
      const delay = animated ? i * 40 : 0;
      setTimeout(() => { el.style.width = pct + "%"; }, delay);
    });
  }

  function renderCharts() {
    renderBar("dow-chart", BUNDLE.by_dow || [], DOW, C.rust, C.cream);
    renderBar("hour-chart", BUNDLE.by_hour || [], Array.from({length:24}, (_,i)=>String(i).padStart(2,"0")), C.sage, C.cream);
    renderHeatmap();
  }

  function setupAnimations() {
    animateCounters();
    fillBars(true);
    renderCharts();
    almanacSetupInspectableReceipts();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setupAnimations);
  } else {
    setupAnimations();
  }
  window.addEventListener("resize", () => {
    clearTimeout(window.__almanacResizeTimer);
    window.__almanacResizeTimer = setTimeout(renderCharts, 120);
  });

  // ── Snap navigation: one wheel/key/swipe gesture = one section ─────────
  function setupSnapNav() {
    const sections = [...document.querySelectorAll("section.slide")];
    if (sections.length === 0) return;

    let current = 0;
    let locked = false;
    const COOLDOWN_MS = 850;

    function indexNearestToScroll() {
      const y = window.scrollY + window.innerHeight / 2;
      let best = 0, bestDist = Infinity;
      sections.forEach((s, i) => {
        const center = s.offsetTop + s.offsetHeight / 2;
        const dist = Math.abs(center - y);
        if (dist < bestDist) { bestDist = dist; best = i; }
      });
      return best;
    }

    function goTo(i) {
      i = Math.max(0, Math.min(sections.length - 1, i));
      if (i === current && !locked) {
        // already there — still smooth-correct any drift
      }
      current = i;
      locked = true;
      sections[i].scrollIntoView({ behavior: "smooth", block: "start" });
      setTimeout(() => { locked = false; }, COOLDOWN_MS);
    }

    function step(dir) {
      if (locked) return;
      const here = indexNearestToScroll();
      goTo(here + dir);
    }

    // Wheel — collapse a whole gesture into one step
    window.addEventListener("wheel", (e) => {
      e.preventDefault();
      if (locked) return;
      if (Math.abs(e.deltaY) < 8) return;
      step(e.deltaY > 0 ? 1 : -1);
    }, { passive: false });

    // Keys
    window.addEventListener("keydown", (e) => {
      switch (e.key) {
        case "ArrowDown":
        case "PageDown":
        case " ":
        case "j":
          e.preventDefault(); step(1); break;
        case "ArrowUp":
        case "PageUp":
        case "k":
          e.preventDefault(); step(-1); break;
        case "Home":
          e.preventDefault(); goTo(0); break;
        case "End":
          e.preventDefault(); goTo(sections.length - 1); break;
      }
    });

    // Touch swipe
    let touchStartY = null;
    window.addEventListener("touchstart", (e) => {
      touchStartY = e.touches[0].clientY;
    }, { passive: true });
    window.addEventListener("touchend", (e) => {
      if (touchStartY == null) return;
      const dy = touchStartY - e.changedTouches[0].clientY;
      if (Math.abs(dy) > 40) step(dy > 0 ? 1 : -1);
      touchStartY = null;
    }, { passive: true });

    // Sync `current` if user lands deep-linked
    current = indexNearestToScroll();
    // Settle position to the nearest snap on load.
    requestAnimationFrame(() => goTo(current));
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setupSnapNav);
  } else {
    setupSnapNav();
  }
