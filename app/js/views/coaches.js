// ============================================================
// COACHES VIEW — EuroLeague Fantasy coaches + stats
// ============================================================
(function () {
  "use strict";

  const state = {
    coaches: [],
    filtered: [],
    sortKey: "avg_xp",
    sortDir: "desc",
    query: "",
    teamFilter: null,   // null = όλες
    initialized: false,
    modalEl: null,
  };

  // ---------------- helpers ----------------
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g,
      c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
  function fmt(v, d = 2) {
    if (typeof v !== "number" || !isFinite(v)) return "—";
    return v.toFixed(d);
  }
  function fmtCredits(c) {
    if (c == null || !isFinite(c)) return "—";
    return c.toFixed(1);
  }
  function xpClass(xp) {
    if (!isFinite(xp)) return "";
    if (xp >= 10) return "cz-xp-great";
    if (xp >= 5)  return "cz-xp-good";
    if (xp >= 0)  return "cz-xp-neutral";
    return "cz-xp-bad";
  }
  function formArrow(form) {
    if (!isFinite(form)) return "";
    if (form >= 10) return `<span class="cz-form up">▲</span>`;
    if (form <= -5) return `<span class="cz-form down">▼</span>`;
    return `<span class="cz-form flat">—</span>`;
  }

  // ---------------- styles ----------------
  function injectStyles() {
    if (document.getElementById("cz-styles")) return;
    const s = document.createElement("style");
    s.id = "cz-styles";
    s.textContent = `
      .cz-wrap { padding: 0; font-family: inherit; color: inherit; }

      .cz-toolbar {
        display:flex; gap:10px; flex-wrap:wrap; align-items:center;
        position: sticky;
        top: 0;
        z-index: 50;
        background: var(--card, #fff);
        margin: -24px -24px 14px -24px;
        padding: 14px 24px 12px 24px;
        border-bottom: 1px solid var(--line, #e5e7eb);
        box-shadow: 0 2px 8px rgba(0,0,0,.04);
      }
      .cz-search-wrap {
        position:relative; display:flex; align-items:center;
        flex:1 1 260px; max-width:360px;
        background: var(--card,#fff);
        border:1px solid var(--line,#d1d5db);
        border-radius:999px;
        padding:0 14px;
        transition: border-color .15s, box-shadow .15s;
      }
      .cz-search-wrap:focus-within {
        border-color:#f97316;
        box-shadow: 0 0 0 3px rgba(249,115,22,.15);
      }
      .cz-search-icon { font-size:13px; opacity:.7; margin-right:6px; user-select:none; }
      .cz-search-wrap input {
        flex:1; border:0; outline:0; background:transparent; color:inherit;
        font-size:14px; padding:8px 0; min-width:0;
      }
      .cz-filter-group { display:flex; gap:6px; flex-wrap:wrap; }
      .cz-filter-btn {
        padding:6px 12px; border-radius:999px; cursor:pointer;
        font-size:12px; font-weight:600;
        background: var(--card,#fff); color: inherit;
        border:1px solid var(--line,#e5e7eb);
        transition: all .15s ease;
      }
      .cz-filter-btn:hover { border-color:#f97316; color:#f97316; }
      .cz-filter-btn.on {
        background:#f97316; color:#fff; border-color:#f97316;
        box-shadow: 0 3px 10px rgba(249,115,22,.35);
      }
      .cz-count {
        margin-left:auto; font-size:13px; opacity:.75; white-space:nowrap;
      }

      /* --- Table --- */
      .cz-table { width:100%; border-collapse: collapse; font-size:14px; }
      .cz-table th, .cz-table td {
        padding:8px 10px; text-align:left;
        border-bottom:1px solid var(--line,#e5e7eb);
      }
      .cz-table th {
        cursor:pointer; user-select:none; font-weight:600;
        white-space:nowrap; font-size:12px;
        text-transform:uppercase; letter-spacing:.03em;
      }
      .cz-table th:hover { color: var(--accent,#2563eb); }
      .cz-table th .arrow { font-size:11px; opacity:.6; margin-left:4px; }
      .cz-table tbody tr { cursor:pointer; }
      .cz-table tr:hover td { background: var(--hover,#f3f4f6); }
      .cz-num { text-align:right; font-variant-numeric: tabular-nums; }
      .cz-rank { width:40px; }
      td.cz-rank { opacity:.6; }
      .cz-name { font-weight:600; }
      .cz-credits { font-weight:700; color:#f97316; }
      .cz-xp { font-weight:700; }
      .cz-xp-great   { color:#16a34a; }
      .cz-xp-good    { color:#22c55e; }
      .cz-xp-neutral { color:inherit; opacity:.75; }
      .cz-xp-bad     { color:#dc2626; }
      .cz-form { font-size:11px; margin-left:4px; }
      .cz-form.up   { color:#16a34a; }
      .cz-form.down { color:#dc2626; }
      .cz-form.flat { opacity:.5; }

      /* name badge */
      .cz-name-badge { margin-left:6px; font-size:13px; }

      /* --- Modal --- */
      .cz-modal-bg {
        position:fixed; inset:0; background:rgba(0,0,0,.5);
        display:flex; align-items:center; justify-content:center;
        z-index:9999; padding:20px;
      }
      .cz-modal {
        background:var(--card,#fff); color:inherit;
        border-radius:14px; max-width:640px; width:100%;
        max-height:85vh; overflow:auto; padding:24px;
        box-shadow:0 20px 60px rgba(0,0,0,.3);
        position:relative;
      }
      .cz-modal h2 { margin:0 0 4px 0; font-size:22px; }
      .cz-modal .cz-sub { opacity:.7; font-size:13px; margin-bottom:16px; }
      .cz-modal-grid {
        display:grid; grid-template-columns:repeat(2,1fr);
        gap:10px 20px; margin:16px 0;
      }
      .cz-modal-grid > div {
        display:flex; justify-content:space-between;
        padding:6px 0; border-bottom:1px solid var(--line,#eee);
      }
      .cz-modal-grid span:first-child { opacity:.7; }
      .cz-close {
        position:absolute; top:14px; right:18px;
        background:transparent; border:0; font-size:22px;
        cursor:pointer; color:inherit;
      }
      .cz-history-header {
        margin-top:18px; padding-top:14px;
        border-top:2px solid var(--line,#eee);
      }
      .cz-history-table {
        width:100%; border-collapse:collapse;
        font-size:12.5px; margin-top:8px;
      }
      .cz-history-table th, .cz-history-table td {
        padding:6px 8px; text-align:left;
        border-bottom:1px solid var(--line,#eee);
        white-space:nowrap;
      }
      .cz-history-table th {
        font-weight:600; font-size:11px;
        text-transform:uppercase; opacity:.7;
      }
      .cz-history-table .won  { color:#16a34a; font-weight:700; }
      .cz-history-table .lost { color:#dc2626; font-weight:700; }
      .cz-empty {
        padding:40px; text-align:center; opacity:.6;
      }
    `;
    document.head.appendChild(s);
  }

  // ---------------- normalize ----------------
  function normalize(raw) {
    if (!Array.isArray(raw)) return [];
    return raw.map(c => ({
      name:        c.name || "—",
      team:        c.team || "—",
      teamFull:    c.team_full || "—",
      nationality: c.nationality || "—",
      age:         c.age,
      credits:     c.credits,
      games:       c.games || 0,
      wins:        c.wins || 0,
      losses:      c.losses || 0,
      winPct:      c.win_pct || 0,
      totalXp:     c.total_xp || 0,
      avgXp:       c.avg_xp || 0,
      form:        c.form_last5 || 0,
      history:     c.history || [],
    }));
  }

  // ---------------- filter/sort ----------------
  function apply() {
    const q = state.query.trim().toUpperCase();
    let rows = state.coaches.slice();

    if (q) {
      rows = rows.filter(r =>
        r.name.toUpperCase().includes(q) ||
        r.team.toUpperCase().includes(q) ||
        r.teamFull.toUpperCase().includes(q)
      );
    }
    if (state.teamFilter) {
      rows = rows.filter(r => r.team === state.teamFilter);
    }

    const dir = state.sortDir === "asc" ? 1 : -1;
    const k = state.sortKey;
    rows.sort((a, b) => {
      const av = a[k], bv = b[k];
      if (typeof av === "number" && typeof bv === "number") {
        if (isNaN(av)) return 1;
        if (isNaN(bv)) return -1;
        return (av - bv) * dir;
      }
      return String(av || "").localeCompare(String(bv || "")) * dir;
    });
    state.filtered = rows;
  }

  // ---------------- render table ----------------
  function renderTable() {
    const root = document.getElementById("view-coaches");
    if (!root) return;
    const rows = state.filtered;

    const arrowFor = k => state.sortKey === k ? (state.sortDir === "asc" ? "▲" : "▼") : "";

    // Όλες οι ομάδες για τα filter buttons
    const allTeams = [...new Set(state.coaches.map(c => c.team))].sort();

    const filterBtns = [
      `<button type="button" class="cz-filter-btn ${!state.teamFilter ? 'on' : ''}" data-team="">Όλες</button>`
    ].concat(
      allTeams.map(t =>
        `<button type="button" class="cz-filter-btn ${state.teamFilter === t ? 'on' : ''}" data-team="${esc(t)}">${esc(t)}</button>`
      )
    ).join("");

    const thead = `
      <tr>
        <th class="cz-rank">#</th>
        <th data-sort="name">Coach <span class="arrow">${arrowFor("name")}</span></th>
        <th data-sort="team">Team <span class="arrow">${arrowFor("team")}</span></th>
        <th data-sort="nationality">Nat <span class="arrow">${arrowFor("nationality")}</span></th>
        <th data-sort="age" class="cz-num">Age <span class="arrow">${arrowFor("age")}</span></th>
        <th data-sort="credits" class="cz-num">Credits <span class="arrow">${arrowFor("credits")}</span></th>
        <th data-sort="games" class="cz-num">GP <span class="arrow">${arrowFor("games")}</span></th>
        <th data-sort="wins" class="cz-num">W <span class="arrow">${arrowFor("wins")}</span></th>
        <th data-sort="losses" class="cz-num">L <span class="arrow">${arrowFor("losses")}</span></th>
        <th data-sort="winPct" class="cz-num">Win% <span class="arrow">${arrowFor("winPct")}</span></th>
        <th data-sort="avgXp" class="cz-num">Avg xP <span class="arrow">${arrowFor("avgXp")}</span></th>
        <th data-sort="form" class="cz-num">Form <span class="arrow">${arrowFor("form")}</span></th>
        <th data-sort="totalXp" class="cz-num">Total xP <span class="arrow">${arrowFor("totalXp")}</span></th>
      </tr>`;

    const tbody = rows.length
      ? rows.map((r, i) => `
        <tr data-team="${esc(r.team)}">
          <td class="cz-rank">${i + 1}</td>
          <td class="cz-name">${esc(r.name)}</td>
          <td>${esc(r.team)}</td>
          <td>${esc(r.nationality)}</td>
          <td class="cz-num">${r.age != null ? r.age : "—"}</td>
          <td class="cz-num cz-credits">${fmtCredits(r.credits)}</td>
          <td class="cz-num">${r.games}</td>
          <td class="cz-num">${r.wins}</td>
          <td class="cz-num">${r.losses}</td>
          <td class="cz-num">${fmt(r.winPct, 1)}%</td>
          <td class="cz-num cz-xp ${xpClass(r.avgXp)}">${fmt(r.avgXp, 2)}${formArrow(r.form)}</td>
          <td class="cz-num">${fmt(r.form, 2)}</td>
          <td class="cz-num ${xpClass(r.totalXp)}">${fmt(r.totalXp, 0)}</td>
        </tr>`).join("")
      : `<tr><td colspan="13" class="cz-empty">Δεν βρέθηκαν προπονητές.</td></tr>`;

    root.innerHTML = `
      <div class="cz-wrap">
        <div class="cz-toolbar">
          <div class="cz-search-wrap">
            <span class="cz-search-icon">🔍</span>
            <input id="czSearch" type="text" placeholder="Αναζήτηση προπονητή ή ομάδας..." value="${esc(state.query)}">
          </div>
          <div class="cz-filter-group">${filterBtns}</div>
          <span class="cz-count">${rows.length} / ${state.coaches.length} coaches</span>
        </div>
        <table class="cz-table">
          <thead>${thead}</thead>
          <tbody>${tbody}</tbody>
        </table>
      </div>`;

    // Events
    root.querySelector("#czSearch").addEventListener("input", e => {
      state.query = e.target.value;
      apply(); renderTable();
      const el = document.getElementById("czSearch");
      if (el) { el.focus(); el.setSelectionRange(el.value.length, el.value.length); }
    });

    root.querySelectorAll(".cz-filter-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const t = btn.dataset.team || null;
        state.teamFilter = (state.teamFilter === t) ? null : t;
        apply(); renderTable();
      });
    });

    root.querySelectorAll("th[data-sort]").forEach(th => {
      th.addEventListener("click", () => {
        const k = th.dataset.sort;
        if (state.sortKey === k) {
          state.sortDir = state.sortDir === "asc" ? "desc" : "asc";
        } else {
          state.sortKey = k;
          state.sortDir = ["name", "team", "nationality"].includes(k) ? "asc" : "desc";
        }
        apply(); renderTable();
      });
    });

    root.querySelectorAll("tbody tr[data-team]").forEach(tr => {
      tr.addEventListener("click", () => {
        const team = tr.dataset.team;
        const c = state.coaches.find(x => x.team === team);
        if (c) openModal(c);
      });
    });
  }

  // ---------------- modal ----------------
  function openModal(c) {
    closeModal();
    const bg = document.createElement("div");
    bg.className = "cz-modal-bg";
    bg.addEventListener("click", e => { if (e.target === bg) closeModal(); });

    const row = (label, val) => `<div><span>${esc(label)}</span><span>${val}</span></div>`;

    const historyRows = c.history.length
      ? c.history.map(h => `
        <tr>
          <td>R${h.round}</td>
          <td>${esc(h.opp)}</td>
          <td>${h.hs}-${h.aw}</td>
          <td class="${h.won ? 'won' : 'lost'}">${h.won ? 'W' : 'L'}</td>
          <td>+${h.margin}</td>
          <td class="${xpClass(h.xp)}">${h.xp > 0 ? '+' : ''}${h.xp}</td>
        </tr>`).join("")
      : `<tr><td colspan="6" class="cz-empty" style="padding:16px">Δεν υπάρχει ιστορικό.</td></tr>`;

    bg.innerHTML = `
      <div class="cz-modal" role="dialog" aria-modal="true">
        <button class="cz-close" aria-label="Close">×</button>
        <h2>${esc(c.name)}</h2>
        <div class="cz-sub">${esc(c.teamFull)} · ${esc(c.nationality)}${c.age != null ? " · " + c.age + " ετών" : ""}</div>
        <div class="cz-modal-grid">
          ${row("Credits",   `<span class="cz-credits">${fmtCredits(c.credits)}</span>`)}
          ${row("Games",     c.games)}
          ${row("Wins",      c.wins)}
          ${row("Losses",    c.losses)}
          ${row("Win %",     fmt(c.winPct, 1) + "%")}
          ${row("Avg xP",    `<span class="${xpClass(c.avgXp)}">${fmt(c.avgXp, 2)}</span>`)}
          ${row("Form L5",   fmt(c.form, 2))}
          ${row("Total xP",  `<span class="${xpClass(c.totalXp)}">${fmt(c.totalXp, 0)}</span>`)}
        </div>
        <div class="cz-history-header">
          <strong>Game History</strong>
        </div>
        <table class="cz-history-table">
          <thead>
            <tr>
              <th>Round</th><th>Opp</th><th>Score</th>
              <th>W/L</th><th>Margin</th><th>xP</th>
            </tr>
          </thead>
          <tbody>${historyRows}</tbody>
        </table>
      </div>`;

    document.body.appendChild(bg);
    state.modalEl = bg;
    bg.querySelector(".cz-close").addEventListener("click", closeModal);
    document.addEventListener("keydown", escClose);
  }
  function escClose(e) { if (e.key === "Escape") closeModal(); }
  function closeModal() {
    if (state.modalEl) { state.modalEl.remove(); state.modalEl = null; }
    document.removeEventListener("keydown", escClose);
  }

  // ---------------- entry ----------------
  function renderCoaches() {
    injectStyles();
    const root = document.getElementById("view-coaches");
    if (!root) return;

    if (!state.initialized) {
      const raw = window.COACHES;
      if (!raw) {
        root.innerHTML = `<div class="cz-wrap"><div class="cz-empty">
          Δεν βρέθηκαν δεδομένα (window.COACHES).
        </div></div>`;
        return;
      }
      state.coaches = normalize(raw);
      state.initialized = true;
    }

    apply();
    renderTable();
  }

  window.renderCoaches = renderCoaches;
})();