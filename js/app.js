/* Tickmark: static practice site. No data leaves the browser. */
(function () {
  "use strict";

  const BANK = window.BANK;
  const INTERP = window.INTERP;
  const QMAP = Object.fromEntries(BANK.questions.map(q => [q.id, q]));
  const main = document.getElementById("main");
  const pg = () => document.getElementById("page");

  const MANIP_MINUTES = 20;   // suggested time for a data manipulation exam
  const INTERP_MINUTES = 10;  // suggested time for a data interpretation exam

  // ------------------------------------------------------------ helpers
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  // minimal inline markup: `code`
  const md = s => esc(s).replace(/`([^`]+)`/g, "<code>$1</code>");
  const fmtSize = b => b >= 1e6 ? (b / 1e6).toFixed(1).replace(".0", "") + " MB" : Math.max(1, Math.round(b / 1e3)) + " KB";
  const fileName = f => f.split("/").pop();
  const levelText = n => ["", "Basic", "Intermediate", "Advanced"][n] || "";
  const fmtNum = (v, dp) => Number(v).toLocaleString("en-US", { minimumFractionDigits: dp, maximumFractionDigits: dp });
  const dpOf = v => { const s = String(v); return s.includes(".") ? s.split(".")[1].length : 0; };

  function datasetQuestions(caseId) { return BANK.questions.filter(q => q.case === caseId); }

  // ------------------------------------------------------------ answer parsing
  // Accepts 1,086,734.19 / 1.086.734,19 / 1086734,19 / $47 400 000 / (157,882.08) / 7.84%
  function parseNumber(raw) {
    let s = String(raw).trim().toLowerCase();
    if (!s) return null;
    let neg = false;
    if (/^\(.*\)$/.test(s)) { neg = true; s = s.slice(1, -1); }
    s = s.replace(/usd|dkk|kr\.?|\$|€|%|hours?|minutes?|days?|years?/g, "").replace(/[\s\u00a0'’]/g, "");
    s = s.replace(/[\u2212\u2013]/g, "-");
    if (s.startsWith("-")) { neg = !neg; s = s.slice(1); }
    if (!/^[0-9.,]+$/.test(s)) return null;
    const hasC = s.includes(","), hasD = s.includes(".");
    if (hasC && hasD) {
      if (s.lastIndexOf(",") > s.lastIndexOf(".")) s = s.replace(/\./g, "").replace(",", ".");
      else s = s.replace(/,/g, "");
    } else if (hasC) {
      s = /^\d{1,3}(,\d{3})+$/.test(s) ? s.replace(/,/g, "") : s.replace(",", ".");
    } else if (hasD && /^\d{1,3}(\.\d{3}){2,}$/.test(s)) {
      s = s.replace(/\./g, "");
    }
    const v = Number(s);
    if (!isFinite(v)) return null;
    return neg ? -v : v;
  }

  const MONTHS = { jan: 1, feb: 2, mar: 3, apr: 4, may: 5, maj: 5, jun: 6, jul: 7, aug: 8, sep: 9, oct: 10, okt: 10, nov: 11, dec: 12 };
  // Returns every plausible reading [y,m,d,h,mi] of a date string
  function parseDates(raw) {
    const s = String(raw).trim().toLowerCase().replace(/\s+/g, " ").replace(/\bkl\.?\s*/, "");
    const out = [];
    // a time at the end, separated from the date by a space or "t"
    const time = s.match(/[ t,](\d{1,2})[:.](\d{2})(?::\d{2})?\s*(am|pm)?$/);
    let h = null, mi = null, rest = s;
    if (time) {
      h = +time[1]; mi = +time[2];
      if (time[3] === "pm" && h < 12) h += 12;
      if (time[3] === "am" && h === 12) h = 0;
      rest = s.slice(0, time.index).replace(/[ t,]+$/, "");
    }
    let m;
    if ((m = rest.match(/^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$/))) out.push([+m[1], +m[2], +m[3]]);
    else if ((m = rest.match(/^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})$/))) {
      let y = +m[3]; if (y < 100) y += 2000;
      out.push([y, +m[2], +m[1]]); // day first (Danish/European)
      out.push([y, +m[1], +m[2]]); // month first (US)
    } else if ((m = rest.match(/^(\d{1,2})\.? ([a-zæøå]+)\.? (\d{4})$/)) && MONTHS[m[2].slice(0, 3)]) {
      out.push([+m[3], MONTHS[m[2].slice(0, 3)], +m[1]]);
    } else if ((m = rest.match(/^([a-z]+)\.? (\d{1,2}),? (\d{4})$/)) && MONTHS[m[1].slice(0, 3)]) {
      out.push([+m[3], MONTHS[m[1].slice(0, 3)], +m[2]]);
    }
    return out.map(d => d.concat([h, mi]));
  }

  const normText = s => String(s).trim().toLowerCase().replace(/^["'“”]+|["'“”.]+$/g, "").replace(/\s+/g, " ");

  // result: { ok: bool, msg: string } or { invalid: msg }
  function check(spec, raw) {
    if (spec.type === "number" || spec.type === "percent") {
      const v = parseNumber(raw);
      if (v === null) return { invalid: "Enter a number, for example 1234.56 or 1.234,56." };
      if (spec.type === "percent") {
        const asFraction = String(raw).includes("%") ? [v / 100] : [v, v / 100];
        return { ok: asFraction.some(x => Math.abs(x - spec.value) <= spec.tol + 1e-9) };
      }
      return { ok: Math.abs(v - spec.value) <= spec.tol + 1e-9 };
    }
    if (spec.type === "date") {
      const reads = parseDates(raw);
      if (!reads.length) return { invalid: "Enter a date such as 2011-12-07 16:38 or 07-12-2011 16:38." };
      const [y, mo, d, h, mi] = spec.value;
      if (h !== null && reads.every(r => r[3] === null)) return { invalid: "Include the time as well, for example 16:38." };
      return { ok: reads.some(r => r[0] === y && r[1] === mo && r[2] === d && (h === null || (r[3] === h && r[4] === mi))) };
    }
    if (spec.type === "text") {
      if (!String(raw).trim()) return { invalid: "Enter an answer first." };
      return { ok: spec.accept.some(a => normText(a) === normText(raw)) };
    }
    if (spec.type === "choice") {
      if (!raw) return { invalid: "Choose an option first." };
      return { ok: raw === spec.correct };
    }
    return { ok: false };
  }

  function keyText(spec, unit) {
    const u = unit || spec.unit || "";
    if (spec.type === "number") {
      const dp = Math.abs(spec.value) >= 100 ? Math.min(2, dpOf(spec.value)) : Math.min(4, dpOf(spec.value));
      const tol = spec.tol > 0 ? Number(spec.tol.toPrecision(2)) : 0;
      return fmtNum(spec.value, dp) + (u ? " " + u : "") + (tol ? ` (accepted within ±${tol})` : "");
    }
    if (spec.type === "percent") return fmtNum(spec.value * 100, Math.max(0, dpOf(spec.value) - 2)) + "%";
    if (spec.type === "date") {
      const [y, m, d, h, mi] = spec.value;
      const date = `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
      return h === null ? date : `${date} ${String(h).padStart(2, "0")}:${String(mi).padStart(2, "0")}`;
    }
    if (spec.type === "text") return spec.accept[0];
    if (spec.type === "choice") return spec.correct;
    return "";
  }

  function inputHint(spec) {
    return { number: "Number", percent: "Percentage", date: spec.value && spec.value[3] !== null ? "Date and time" : "Date", text: "Text" }[spec.type] || "";
  }

  // ------------------------------------------------------------ marks (auditor tickmarks)
  const TICK = '<path d="M6 19l8 9L32 7"/>';
  const CROSS = '<path d="M9 9l20 20"/><path d="M29 9L9 29"/>';
  function setMark(sheet, ok) {
    let svg = sheet.querySelector(".mark");
    if (!svg) {
      svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svg.setAttribute("viewBox", "0 0 38 38"); svg.setAttribute("aria-hidden", "true");
      sheet.prepend(svg);
    }
    svg.setAttribute("class", "mark");
    svg.innerHTML = ok ? TICK : CROSS;
    void svg.getBoundingClientRect();
    svg.classList.add("draw");
  }

  // ------------------------------------------------------------ sheet rendering
  // A "sheet" is one question on a workpaper. ctx.onResult(id, ok) lets exams keep score.
  function bankSheet(q, opts = {}) {
    const ds = BANK.datasets[q.case];
    const ref = opts.link === false ? esc(q.id) : `<a href="#/questions/${q.id}">${esc(q.id)}</a>`;
    const sol = q.sql
      ? `<p class="key">Answer: ${esc(keyText(q.answer))}</p><pre class="sql"><code>${esc(q.sql)}</code></pre>`
      : `<p class="key">Answer: ${esc(keyText(q.answer))}</p><ol>${q.steps.map(s => `<li>${md(s)}</li>`).join("")}</ol>`;
    return `
    <article class="sheet" data-qid="${esc(q.id)}" aria-labelledby="h-${esc(q.id)}">
      <div class="sheet-head">
        <span class="ref" id="h-${esc(q.id)}">${opts.number ? `Question ${opts.number}` : ""}${opts.number ? ` <span class="muted">(${ref})</span>` : ref}</span>
        <span class="tag ${q.tool.toLowerCase()}">${esc(q.tool)}</span>
        <span class="where">${esc(ds.name)}, ${esc(q.topic)}, ${levelText(q.level).toLowerCase()}</span>
      </div>
      ${q.setup ? `<p class="setup"><strong>Before you start:</strong> ${md(q.setup)}</p>` : ""}
      <p class="prompt">${md(q.prompt)}</p>
      ${answerControls(q.id, q.answer)}
      <div class="feedback" role="status" aria-live="polite"></div>
      <details class="solution"><summary>Show solution</summary>${sol}</details>
    </article>`;
  }

  function answerControls(id, spec, unit) {
    const u = unit || spec.unit || "";
    if (spec.type === "choice") {
      return `<fieldset class="choices"><legend class="small muted">Choose one</legend>${spec.options.map((o, i) =>
        `<label><input type="radio" name="c-${esc(id)}" value="${esc(o)}"> <span>${esc(o)}</span></label>`).join("")}</fieldset>
        <div class="btn-row"><button class="btn" data-act="check">Check answer</button></div>`;
    }
    if (spec.type === "open") {
      return `<label class="small muted" for="a-${esc(id)}">Your answer</label>
        <textarea id="a-${esc(id)}" rows="3"></textarea>
        <div class="btn-row" style="margin-top:.6rem"><button class="btn" data-act="reveal">Compare with model answer</button></div>`;
    }
    return `<div class="answer-row">
        <label class="field"><span>${inputHint(spec)}${u ? ` (${esc(u)})` : ""}</span>
          <input type="text" id="a-${esc(id)}" autocomplete="off" spellcheck="false" inputmode="${spec.type === "text" ? "text" : "decimal"}"></label>
        <button class="btn" data-act="check">Check answer</button>
      </div>`;
  }

  // Wire up all sheets inside root. getSpec(id) returns {spec, unit}.
  function wireSheets(root, getSpec, onResult) {
    root.addEventListener("click", e => {
      const btn = e.target.closest("[data-act]");
      if (!btn) return;
      const sheet = btn.closest(".sheet");
      const id = sheet.dataset.qid;
      const { spec, unit } = getSpec(id);
      const fb = sheet.querySelector(".feedback");
      const act = btn.dataset.act;

      if (act === "check") {
        const raw = spec.type === "choice"
          ? (sheet.querySelector("input[type=radio]:checked") || {}).value
          : sheet.querySelector("input[type=text]").value;
        const r = check(spec, raw);
        if (r.invalid) { fb.className = "feedback no"; fb.textContent = r.invalid; return; }
        setMark(sheet, r.ok);
        fb.className = "feedback " + (r.ok ? "ok" : "no");
        fb.innerHTML = r.ok
          ? `Correct. <span class="detail">Expected ${esc(keyText(spec, unit))}.</span>`
          : `Not this one. <span class="detail">Try again, or open the solution to see where it differs.</span>`;
        onResult && onResult(id, r.ok);
      }
      if (act === "reveal") {
        const box = sheet.querySelector(".model-box");
        box.hidden = false;
        btn.hidden = true;
        box.querySelector("[data-act=self-ok]").focus();
      }
      if (act === "self-ok" || act === "self-no") {
        const ok = act === "self-ok";
        setMark(sheet, ok);
        fb.className = "feedback " + (ok ? "ok" : "no");
        fb.textContent = ok ? "Marked as covered." : "Marked as missed. Read the model answer once more.";
        onResult && onResult(id, ok);
      }
    });
    root.addEventListener("keydown", e => {
      if (e.key === "Enter" && e.target.matches(".sheet input[type=text]")) {
        e.preventDefault();
        e.target.closest(".sheet").querySelector("[data-act=check]").click();
      }
    });
  }

  // ------------------------------------------------------------ timer
  function timerHTML(minutes) {
    return `<div class="timer" role="group" aria-label="Exam timer">
      <span class="clock" aria-live="off">00:00</span>
      <span class="meta">Suggested time: ${minutes} minutes. The clock turns red when you pass it.</span>
      <div class="btn-row">
        <button class="btn secondary" data-timer="toggle">Start</button>
        <button class="btn quiet" data-timer="reset">Reset</button>
      </div>
      <span class="sr-status" role="status" style="position:absolute;left:-9999px"></span>
    </div>`;
  }
  let timerHandle = null;
  function wireTimer(root, minutes) {
    const box = root.querySelector(".timer");
    const clock = box.querySelector(".clock");
    const toggle = box.querySelector("[data-timer=toggle]");
    const status = box.querySelector(".sr-status");
    let elapsed = 0, startedAt = null, announced = false;
    const show = () => {
      const s = Math.floor((elapsed + (startedAt ? Date.now() - startedAt : 0)) / 1000);
      clock.textContent = String(Math.floor(s / 60)).padStart(2, "0") + ":" + String(s % 60).padStart(2, "0");
      const over = s >= minutes * 60;
      box.classList.toggle("over", over);
      if (over && !announced) { announced = true; status.textContent = "Suggested time reached."; }
    };
    toggle.addEventListener("click", () => {
      if (startedAt) { elapsed += Date.now() - startedAt; startedAt = null; clearInterval(timerHandle); toggle.textContent = "Resume"; }
      else { startedAt = Date.now(); timerHandle = setInterval(show, 250); toggle.textContent = "Pause"; }
      show();
    });
    box.querySelector("[data-timer=reset]").addEventListener("click", () => {
      clearInterval(timerHandle); elapsed = 0; startedAt = null; announced = false; toggle.textContent = "Start"; show();
    });
  }

  function scoreHTML(total) {
    return `<section class="score" aria-live="polite"><strong class="score-num">0 of ${total}</strong> <span class="muted">questions marked correct so far.</span></section>`;
  }
  function scoreKeeper(root, total) {
    const res = {};
    return (id, ok) => {
      res[id] = ok;
      const n = Object.values(res).filter(Boolean).length;
      root.querySelector(".score-num").textContent = `${n} of ${total}`;
    };
  }

  function filesList(caseIds) {
    const items = [];
    [...new Set(caseIds)].forEach(c => {
      const d = BANK.datasets[c];
      d.files.forEach((f, i) => items.push(`<li><a href="data/${f}" download>${esc(fileName(f))}</a> <span class="muted small">${fmtSize(d.sizes[i])}, ${esc(d.name)}</span></li>`));
    });
    return `<ul class="files">${items.join("")}</ul>`;
  }

  // ------------------------------------------------------------ pages
  function home() {
    const nQ = BANK.questions.length, nE = BANK.exams.length, nI = INTERP.length;
    return `
    <section class="hero">
      <h1>The exam questions are <span class="tick-word">already here<svg viewBox="0 0 300 30" preserveAspectRatio="none" aria-hidden="true"><path d="M4 20 C 80 8, 190 6, 296 14"/></svg></span>.</h1>
      <p class="lede">At the oral exam you receive one data manipulation exam and one data interpretation exam. They are built from the same questions you can practise below, using only the course cases and datasets.</p>
    </section>
    <div class="paths">
      <section class="path">
        <span class="count">${nE}</span>
        <h2>Data manipulation exams</h2>
        <p>Each exam has two Excel and two SQL questions from the ${nQ}-question bank. Download the files, solve them in Excel or your SQL tool, and check your answers.</p>
        <div class="btn-row"><a class="btn" href="#/exams">Open the exams</a><a class="btn secondary" href="#/questions">Browse all ${nQ} questions</a></div>
      </section>
      <section class="path">
        <span class="count">${nI}</span>
        <h2>Data interpretation exams</h2>
        <p>Read a regression output in the Excel format, make predictions, judge significance and explain what the results mean to a manager.</p>
        <div class="btn-row"><a class="btn" href="#/interpretation">Open the exams</a></div>
      </section>
    </div>
    <h2>How to practise</h2>
    <ol class="steps">
      <li><span>Open an exam and start the timer. Each exam lists the files you need.</span></li>
      <li><span>Solve each question in Excel or SQL, the way you would at the exam.</span></li>
      <li><span>Type your result and check it. Numbers can be written as 1,234.56 or 1.234,56.</span></li>
      <li><span>Open the solution to compare your approach with a worked one.</span></li>
    </ol>`;
  }

  function examsList() {
    const rows = BANK.exams.map(e => {
      const qs = e.questions.map(id => QMAP[id]);
      const ex = qs.filter(q => q.tool === "Excel").map(q => BANK.datasets[q.case].name);
      const sq = qs.filter(q => q.tool === "SQL").map(q => BANK.datasets[q.case].name);
      return `<tr class="link-row" data-href="#/exams/${e.id}">
        <td class="ref"><a href="#/exams/${e.id}">Exam ${e.id}</a></td>
        <td>${esc(ex.join(" and "))}</td><td>${esc(sq.join(" and "))}</td>
        <td class="hide-sm">${qs.map(q => esc(q.id)).join(", ")}</td></tr>`;
    }).join("");
    return `
    <h1>Data manipulation exams</h1>
    <p class="lede">Twelve exams, each with two Excel and two SQL questions. Suggested time: ${MANIP_MINUTES} minutes.</p>
    <div class="btn-row"><button class="btn" id="pick">Choose one for me</button></div>
    <div class="table-wrap"><table class="ledger">
      <thead><tr><th>Exam</th><th>Excel cases</th><th>SQL databases</th><th class="hide-sm">Questions</th></tr></thead>
      <tbody>${rows}</tbody></table></div>`;
  }

  function examPage(id) {
    const e = BANK.exams.find(x => x.id === id);
    if (!e) return notFound();
    const qs = e.questions.map(i => QMAP[i]);
    return `
    <div class="exam-head">
      <div><p class="small muted" style="margin:0"><a href="#/exams">Data manipulation exams</a></p>
      <h1>Exam ${esc(e.id)}</h1></div>
    </div>
    <section aria-labelledby="files-h">
      <h3 id="files-h">Files you need</h3>
      ${filesList(qs.map(q => q.case))}
      <p class="small muted" style="margin-top:.5rem">Zipped databases must be unzipped first. Open .db and .sqlite files in DB Browser for SQLite.</p>
    </section>
    ${timerHTML(MANIP_MINUTES)}
    ${qs.map((q, i) => bankSheet(q, { number: i + 1 })).join("")}
    ${scoreHTML(qs.length)}
    <div class="pager">${neighbour(BANK.exams, e.id, "#/exams/", "Exam ")}</div>`;
  }

  function neighbour(list, id, base, label) {
    const i = list.findIndex(x => x.id === id);
    const prev = list[i - 1], next = list[i + 1];
    return `<span>${prev ? `<a href="${base}${prev.id}">Previous: ${label}${esc(prev.id)}</a>` : ""}</span>
            <span>${next ? `<a href="${base}${next.id}">Next: ${label}${esc(next.id)}</a>` : ""}</span>`;
  }

  // question bank with filters (filters kept in memory for the session)
  const filt = { tool: "All", ds: "", text: "" };
  function questionsPage() {
    const opts = Object.entries(BANK.datasets).map(([k, d]) => `<option value="${k}" ${filt.ds === k ? "selected" : ""}>${esc(d.name)} (${d.tool})</option>`).join("");
    return `
    <h1>Question bank</h1>
    <p class="lede">All ${BANK.questions.length} data manipulation questions. Exams are combinations of these.</p>
    <div class="toolbar">
      <div class="field"><span id="tool-l">Tool</span>
        <div class="seg" role="group" aria-labelledby="tool-l">${["All", "Excel", "SQL"].map(t => `<button data-tool="${t}" aria-pressed="${filt.tool === t}">${t}</button>`).join("")}</div></div>
      <label class="field"><span>Dataset</span><select id="ds"><option value="">All datasets</option>${opts}</select></label>
      <label class="field"><span>Search</span><input type="search" id="qsearch" value="${esc(filt.text)}" placeholder="e.g. split purchase"></label>
    </div>
    <p class="small muted" id="qcount" role="status"></p>
    <div id="qlist"></div>`;
  }
  function renderQList() {
    const t = filt.text.trim().toLowerCase();
    const qs = BANK.questions.filter(q =>
      (filt.tool === "All" || q.tool === filt.tool) && (!filt.ds || q.case === filt.ds) &&
      (!t || (q.prompt + " " + q.topic + " " + q.id).toLowerCase().includes(t)));
    document.getElementById("qcount").textContent = `${qs.length} question${qs.length === 1 ? "" : "s"}`;
    const list = document.getElementById("qlist");
    if (!qs.length) { list.innerHTML = `<p class="empty">No questions match. Clear the search or choose another dataset.</p>`; return; }
    const groups = {};
    qs.forEach(q => (groups[q.case] = groups[q.case] || []).push(q));
    list.innerHTML = Object.entries(groups).map(([c, items]) => `
      <h2>${esc(BANK.datasets[c].name)} <span class="tag ${BANK.datasets[c].tool.toLowerCase()}">${BANK.datasets[c].tool}</span></h2>
      <div class="table-wrap"><table class="ledger"><tbody>
      ${items.map(q => `<tr class="link-row" data-href="#/questions/${q.id}">
        <td class="ref"><a href="#/questions/${q.id}">${esc(q.id)}</a></td>
        <td>${md(q.prompt)}</td>
        <td class="hide-sm muted small">${esc(q.topic)}</td>
        <td class="hide-sm level">${levelText(q.level)}</td></tr>`).join("")}
      </tbody></table></div>`).join("");
  }

  function questionPage(id) {
    const q = QMAP[id];
    if (!q) return notFound();
    const same = datasetQuestions(q.case);
    const ds = BANK.datasets[q.case];
    return `
    <p class="small muted" style="margin:0"><a href="#/questions">Question bank</a></p>
    <h1>${esc(q.id)}: ${esc(ds.name)}</h1>
    <section><h3>Files</h3>${filesList([q.case])}</section>
    ${bankSheet(q, { link: false })}
    <div class="pager">${neighbour(same, q.id, "#/questions/", "")}</div>`;
  }

  // ------------------------------------------------------------ interpretation
  const f4 = v => {
    const a = Math.abs(v);
    if (a !== 0 && (a < 0.0001 || a >= 1e9)) return v.toExponential(2).replace("e", "E");
    return fmtNum(v, a >= 1000 ? 2 : 4);
  };
  function outputHTML(o) {
    const s = o.stats, a = o.anova;
    return `<div class="output">
      <h3>SUMMARY OUTPUT</h3><p class="small muted" style="margin:0 0 .75rem">Dependent variable: ${esc(o.y)}</p>
      <div class="table-wrap"><table class="xl"><caption>Regression Statistics</caption><tbody>
        <tr><td>Multiple R</td><td>${f4(s.multipleR)}</td></tr>
        <tr><td>R Square</td><td>${f4(s.r2)}</td></tr>
        <tr><td>Adjusted R Square</td><td>${f4(s.adjR2)}</td></tr>
        <tr><td>Standard Error</td><td>${f4(s.se)}</td></tr>
        <tr><td>Observations</td><td>${s.n}</td></tr></tbody></table></div>
      <div class="table-wrap"><table class="xl"><caption>ANOVA</caption>
        <thead><tr><th></th><th>df</th><th>SS</th><th>MS</th><th>F</th><th>Significance F</th></tr></thead><tbody>
        <tr><td>Regression</td><td>${a.reg[0]}</td><td>${f4(a.reg[1])}</td><td>${f4(a.reg[2])}</td><td>${f4(a.reg[3])}</td><td>${f4(a.reg[4])}</td></tr>
        <tr><td>Residual</td><td>${a.res[0]}</td><td>${f4(a.res[1])}</td><td>${f4(a.res[2])}</td><td></td><td></td></tr>
        <tr><td>Total</td><td>${a.tot[0]}</td><td>${f4(a.tot[1])}</td><td></td><td></td><td></td></tr></tbody></table></div>
      <div class="table-wrap"><table class="xl">
        <thead><tr><th></th><th>Coefficients</th><th>Standard Error</th><th>t Stat</th><th>P-value</th><th>Lower 95%</th><th>Upper 95%</th></tr></thead><tbody>
        ${o.coef.map(r => `<tr><td>${esc(r.name)}</td><td>${f4(r.coef)}</td><td>${f4(r.se)}</td><td>${f4(r.t)}</td><td>${f4(r.p)}</td><td>${f4(r.lo)}</td><td>${f4(r.hi)}</td></tr>`).join("")}
      </tbody></table></div>${sciNote(o)}</div>`;
  }

  // Excel shows tiny numbers in scientific notation; explain one from this table
  function sciNote(o) {
    const vals = [o.anova.reg[4]].concat(o.coef.map(r => r.p));
    const v = vals.find(x => x !== 0 && Math.abs(x) < 0.0001);
    if (v === undefined) return "";
    const shown = f4(v);                      // e.g. 2.50E-7
    const [m, e] = shown.split("E");
    const k = -Number(e);                     // 7
    const digits = m.replace(".", "").replace(/0+$/, "");   // "25"
    const plainText = k <= 9
      ? "0." + "0".repeat(k - 1) + digits     // 0.00000025
      : `0.000…${digits}, with ${k - 1} zeros after the decimal point`;
    return `<p class="small muted" style="margin:.25rem 0 0">Like Excel, very small numbers are shown in scientific notation. ${shown} means ${m} × 10<sup>${e}</sup> = ${plainText}, far below 0.05.</p>`;
  }

  function interpList() {
    return `
    <h1>Data interpretation exams</h1>
    <p class="lede">Six regression outputs built on scenarios from the course cases. Data is synthetic, so you only need the output on the page. Suggested time: ${INTERP_MINUTES} minutes.</p>
    <div class="btn-row"><button class="btn" id="pick-i">Choose one for me</button></div>
    <div class="table-wrap"><table class="ledger">
      <thead><tr><th>Exam</th><th>Scenario</th><th class="hide-sm">Explanatory variables</th></tr></thead>
      <tbody>${INTERP.map(e => `<tr class="link-row" data-href="#/interpretation/${e.id}">
        <td class="ref"><a href="#/interpretation/${e.id}">Exam ${e.id}</a></td><td>${esc(e.title)}</td>
        <td class="hide-sm muted">${e.output.coef.slice(1).map(c => esc(c.name)).join(", ")}</td></tr>`).join("")}</tbody>
    </table></div>`;
  }

  function interpPage(id) {
    const e = INTERP.find(x => x.id === id);
    if (!e) return notFound();
    const sheets = e.questions.map((q, i) => {
      const qid = `${e.id}-${i + 1}`;
      const isOpen = q.answer.type === "open";
      return `<article class="sheet" data-qid="${qid}" aria-labelledby="h-${qid}">
        <div class="sheet-head"><span class="ref" id="h-${qid}">Question ${i + 1}</span></div>
        <p class="prompt">${md(q.prompt)}</p>
        ${answerControls(qid, q.answer, q.unit)}
        ${isOpen ? `<div class="model-box" hidden>
            <div class="model"><p class="key" style="margin:0 0 .4rem">Model answer</p><p style="margin:0">${md(q.answer.model)}</p></div>
            <p class="small muted">${md(q.explain)}</p>
            <div class="btn-row"><span class="small">Did your answer cover this?</span>
              <button class="btn secondary" data-act="self-ok">Yes, mark it covered</button>
              <button class="btn quiet" data-act="self-no">No, I missed something</button></div></div>` : ""}
        <div class="feedback" role="status" aria-live="polite"></div>
        ${isOpen ? "" : `<details class="solution"><summary>Show solution</summary><p class="key">Answer: ${esc(keyText(q.answer, q.unit))}</p><p>${md(q.explain)}</p></details>`}
      </article>`;
    }).join("");
    return `
    <p class="small muted" style="margin:0"><a href="#/interpretation">Data interpretation exams</a></p>
    <h1>Exam ${esc(e.id)}: ${esc(e.title)}</h1>
    <p>${md(e.scenario)}</p>
    <ul class="vars">${e.variables.map(v => `<li><b>${esc(v[0])}</b><span>${md(v[1])}</span></li>`).join("")}</ul>
    ${outputHTML(e.output)}
    ${timerHTML(INTERP_MINUTES)}
    ${sheets}
    ${scoreHTML(e.questions.length)}
    <div class="pager">${neighbour(INTERP, e.id, "#/interpretation/", "Exam ")}</div>`;
  }

  function datasetsPage() {
    return `
    <h1>Datasets</h1>
    <p class="lede">Every file used by the questions, taken from the course cases.</p>
    ${Object.entries(BANK.datasets).map(([k, d]) => `
      <section class="sheet plain">
        <div class="sheet-head"><h2 style="margin:0;font-size:var(--step-1)">${esc(d.name)}</h2><span class="tag ${d.tool.toLowerCase()}">${d.tool}</span><span class="where">${esc(d.source)}</span></div>
        <p>${esc(d.about)}</p>
        ${filesList([k])}
        <p style="margin:.75rem 0 0"><a href="#/questions" data-ds="${k}">${datasetQuestions(k).length} questions use this dataset</a></p>
      </section>`).join("")}`;
  }

  function notFound() {
    return `<h1>Page not found</h1><p>This address does not match an exam or question. <a href="#/">Go to the start page</a>.</p>`;
  }

  // ------------------------------------------------------------ router
  function route() {
    clearInterval(timerHandle);
    const parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
    const [page, id] = parts;
    let html, after = () => {};
    let titleBits = [];

    switch (page) {
      case undefined: html = home(); break;
      case "exams":
        if (id) {
          html = examPage(id); titleBits = ["Exam " + id];
          after = () => {
            const total = (BANK.exams.find(x => x.id === id) || { questions: [] }).questions.length;
            if (!total) return;
            wireTimer(pg(), MANIP_MINUTES);
            wireSheets(pg(), qid => ({ spec: QMAP[qid].answer }), scoreKeeper(pg(), total));
          };
        } else {
          html = examsList(); titleBits = ["Data manipulation exams"];
          after = () => document.getElementById("pick").addEventListener("click", () => {
            const e = BANK.exams[Math.floor(Math.random() * BANK.exams.length)];
            location.hash = "#/exams/" + e.id;
          });
        }
        break;
      case "interpretation":
        if (id) {
          html = interpPage(id); titleBits = ["Interpretation exam " + id];
          after = () => {
            const e = INTERP.find(x => x.id === id);
            if (!e) return;
            wireTimer(pg(), INTERP_MINUTES);
            wireSheets(pg(), qid => { const q = e.questions[+qid.split("-")[1] - 1]; return { spec: q.answer, unit: q.unit }; },
              scoreKeeper(pg(), e.questions.length));
          };
        } else {
          html = interpList(); titleBits = ["Data interpretation exams"];
          after = () => document.getElementById("pick-i").addEventListener("click", () => {
            location.hash = "#/interpretation/" + INTERP[Math.floor(Math.random() * INTERP.length)].id;
          });
        }
        break;
      case "questions":
        if (id) {
          html = questionPage(id); titleBits = [id];
          after = () => QMAP[id] && wireSheets(pg(), qid => ({ spec: QMAP[qid].answer }));
        } else {
          html = questionsPage(); titleBits = ["Question bank"];
          after = () => {
            renderQList();
            main.querySelectorAll("[data-tool]").forEach(b => b.addEventListener("click", () => {
              filt.tool = b.dataset.tool;
              main.querySelectorAll("[data-tool]").forEach(x => x.setAttribute("aria-pressed", x === b));
              renderQList();
            }));
            document.getElementById("ds").addEventListener("change", ev => { filt.ds = ev.target.value; renderQList(); });
            document.getElementById("qsearch").addEventListener("input", ev => { filt.text = ev.target.value; renderQList(); });
          };
        }
        break;
      case "datasets":
        html = datasetsPage(); titleBits = ["Datasets"];
        after = () => main.querySelectorAll("[data-ds]").forEach(a => a.addEventListener("click", () => { filt.ds = a.dataset.ds; filt.tool = "All"; filt.text = ""; }));
        break;
      default: html = notFound(); titleBits = ["Not found"];
    }

    main.innerHTML = `<div id="page">${html}</div>`;
    after();
    document.title = (titleBits.length ? titleBits.join(" | ") + " | " : "") + "Tickmark";
    document.querySelectorAll("[data-nav]").forEach(a => {
      if (a.dataset.nav === page) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
    });
    window.scrollTo(0, 0);
    if (page !== undefined) main.focus({ preventScroll: true });
  }

  // whole table rows are clickable; the link inside stays the keyboard target
  main.addEventListener("click", e => {
    const row = e.target.closest("tr.link-row");
    if (row && !e.target.closest("a")) location.hash = row.dataset.href;
  });

  window.addEventListener("hashchange", route);
  route();

  // exposed for the self-test page only
  window.__tickmark = { parseNumber, parseDates, check };
})();
