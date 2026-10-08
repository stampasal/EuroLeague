// ============================================================
// FANTASY VIEW — EuroLeague Fantasy predictions + 2026 stats
// + Coach mode (inline toggle, χωρίς νέο tab)
// + Injury badges (από PLAYER_INJURIES)
// ============================================================
(function () {
  "use strict";

  const state = {
    mode: "players",
    players: [],
    filtered: [],
    sortKey: "xp",
    sortDir: "desc",
    query: "",
    positions: ["C", "F", "G"],
    coaches: [],
    coachFiltered: [],
    coachSortKey: "avg_xp",
    coachSortDir: "desc",
    coachQuery: "",
    initialized: false,
    modalEl: null,
    glossaryEl: null,
  };

  // ---------------- data discovery ----------------
  function discoverData() {
    const cands = [
      typeof PLAYER_PREDICTIONS !== "undefined" ? PLAYER_PREDICTIONS : null,
      typeof window !== "undefined" ? window.PLAYER_PREDICTIONS : null,
      typeof window !== "undefined" ? window.playerPredictions : null,
    ];
    for (const c of cands) if (c) return c;
    return null;
  }
  function toArray(obj) {
    if (!obj) return [];
    if (Array.isArray(obj)) return obj;
    if (Array.isArray(obj.players)) return obj.players;
    if (Array.isArray(obj.data)) return obj.data;
    return Object.values(obj).filter(v => v && typeof v === "object" && !Array.isArray(v));
  }

  // ---------------- helpers ----------------
  const NAME_KEYS = ["player", "player_name", "name", "PLAYER", "Player"];
  function pname(p) { for (const k of NAME_KEYS) if (p[k]) return String(p[k]); return "?"; }
  function num(v, d = NaN) { return (typeof v === "number" && isFinite(v)) ? v : d; }
  function fmt(v, d = 2) {
    if (typeof v !== "number" || !isFinite(v)) return "—";
    return v.toFixed(d);
  }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g,
      c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
  function confBadge(c) {
    const v = String(c || "").toLowerCase();
    const cls = v === "high" ? "fz-badge fz-badge-high"
              : v === "medium" ? "fz-badge fz-badge-med"
              : v === "low" ? "fz-badge fz-badge-low" : "fz-badge";
    return `<span class="${cls}">${esc(c || "—")}</span>`;
  }
  function trendBadge(label) {
    const v = String(label || "").toLowerCase();
    if (v.includes("ris")) return `<span class="fz-up">▲ Rising</span>`;
    if (v.includes("fal") || v.includes("drop")) return `<span class="fz-down">▼ Falling</span>`;
    if (v.includes("stab") || v.includes("flat")) return `<span class="fz-flat">— Stable</span>`;
    return `<span class="fz-flat">${esc(label || "—")}</span>`;
  }
  function nameBadge(r) {
    if (!r.trend && !r.confEmoji) return "";
    const t = r.trendIcon || "→";
    const cls = r.trend === "Rising" ? "up" : r.trend === "Falling" ? "down" : "flat";
    const trendLabel = r.trend === "Rising" ? "↑ Καλή φόρμα"
                     : r.trend === "Falling" ? "↓ Κακή φόρμα"
                     : "→ Σταθερή απόδοση";
    const confLabel = r.confEmoji === "🟢" ? "🟢 Αξιόπιστη πρόβλεψη"
                    : r.confEmoji === "🟡" ? "🟡 Μέτρια πρόβλεψη"
                    : r.confEmoji === "🔴" ? "🔴 Αβέβαιη πρόβλεψη"
                    : "";
    const title = confLabel ? `${trendLabel} · ${confLabel}` : trendLabel;
    return `<span class="fz-name-badge" title="${esc(title)}"><span class="${cls}">${t}</span>${r.confEmoji || ""}</span>`;
  }

  // ---------------- injury badge ----------------
  function injuryBadgeHtml(r) {
    if (!r.injuryStatus) return "";
    if (r.injuryStatus === "out") {
      return ` <span class="fz-inj-badge out" title="Out: ${esc(r.injuryRound || "")}">OUT</span>`;
    }
    if (["uncertain", "game_time", "doubtful"].includes(r.injuryStatus)) {
      const label = r.injuryStatus.replace("_", "-");
      return ` <span class="fz-inj-badge reduced" title="${esc(label)}: ${esc(r.injuryRound || "")}">?</span>`;
    }
    return "";
  }

  // ---------------- coach helpers ----------------
  function fmtCredits(c) {
    if (c == null || !isFinite(c)) return "—";
    return c.toFixed(1);
  }
  function xpClass(xp) {
    if (!isFinite(xp)) return "";
    if (xp >= 10) return "fz-xp-great";
    if (xp >= 5)  return "fz-xp-good";
    if (xp >= 0)  return "fz-xp-neutral";
    return "fz-xp-bad";
  }
  function formArrow(form) {
    if (!isFinite(form)) return "";
    if (form >= 10) return `<span class="fz-form up">▲</span>`;
    if (form <= -5) return `<span class="fz-form down">▼</span>`;
    return `<span class="fz-form flat">—</span>`;
  }
  function normalizeCoaches(raw) {
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

  // ---------------- GLOSSARY ----------------
  const GLOSSARY = [
    {
      id: "cols",
      title: "Στήλες Table (Players)",
      entries: [
        { term: "PIR", full: "Performance Index Rating", def: "Επίσημος δείκτης αξιολόγησης της EuroLeague." },
        { term: "xP", full: "Expected Points", def: "Η πρόβλεψη του μοντέλου για τους fantasy πόντους του παίκτη στον επόμενο αγώνα." },
        { term: "Next 3", full: "", def: "Οι επόμενοι 3 αγώνες της ομάδας. 🟢 = εντός έδρας · 🔴 = εκτός." },
        { term: "Credits", full: "", def: "Το κόστος του παίκτη στο Fantasy." },
        { term: "Value", full: "", def: "Value = PIR ÷ Credits. Όσο μεγαλύτερο, τόσο πιο συμφέρον." },
        { term: "Avg MIN", full: "Average Minutes", def: "Μέσος όρος λεπτών συμμετοχής." },
        { term: "SFP", full: "", def: "SFP = REB + AST + STL + BLK + FR − TO − PF − BLA." },
        { term: "Usage", full: "Usage Rate (USG%)", def: "Ποσοστό επιθέσεων που περνούν από τον παίκτη." },
        { term: "FG%", full: "Field Goal Percentage", def: "Ποσοστό ευστοχίας στα σουτ." },
        { term: "Color dots", full: "Χρωματικές κουκκίδες", def: "🟢 Top 33% · 🟡 Μεσαίο · 🔴 Bottom 33%." },
      ],
    },
    {
      id: "injuries",
      title: "Τραυματισμοί (Badges)",
      entries: [
        { term: "OUT", full: "", def: "Ο παίκτης είναι τραυματίας και δεν θα παίξει. Ο optimizer τον αποκλείει αυτόματα." },
        { term: "?", full: "", def: "Ο παίκτης είναι αμφίβολος (Uncertain / Game-time / Doubtful). Ο optimizer μειώνει το xP του στο μισό (×0.5)." },
        { term: "Πηγή", full: "", def: "BasketNews EuroLeague Injury Report — ανανεώνεται αυτόματα με το fetch_injuries.py." },
      ],
    },
    {
      id: "coaches",
      title: "Coach Mode",
      entries: [
        { term: "Πώς μπαίνω", full: "", def: "Πάτα το κουμπί <strong>Coach</strong> δίπλα στα Center/Forward/Guard. Ο πίνακας αλλάζει σε προπονητές." },
        { term: "Πώς βγαίνω", full: "", def: "Πάτα οποιοδήποτε από τα Center / Forward / Guard. Αυτόματα επιστρέφεις στους παίκτες." },
        { term: "Credits", full: "", def: "Το κόστος του προπονητή στο Fantasy." },
        { term: "Avg xP", full: "Average Expected Points", def: "Μέσοι fantasy πόντοι ανά αγώνα. Υπολογισμένο από τα αποτελέσματα: +25 νίκη 20+, +20 νίκη 11-20, +10 νίκη 1-10, -5 ήττα 1-10, -10 ήττα 11-20, -20 ήττα 20+." },
        { term: "Form", full: "Last 5 form", def: "Μέσος όρος xP στα τελευταία 5 παιχνίδια." },
        { term: "W / L", full: "Wins / Losses", def: "Νίκες και ήττες." },
        { term: "Win %", full: "", def: "Ποσοστό νικών." },
        { term: "Total xP", full: "", def: "Άθροισμα xP σε όλα τα παιχνίδια." },
      ],
    },
    {
      id: "badges",
      title: "Badges (δίπλα στο όνομα)",
      entries: [
        { term: "Τάση (Trend)", full: "", def: [
          "↑ Καλή φόρμα: ο παίκτης ανεβαίνει.",
          "→ Σταθερή απόδοση.",
          "↓ Κακή φόρμα: ο παίκτης πέφτει."
        ] },
        { term: "Σιγουριά (Confidence)", full: "", def: [
          "🟢 Αξιόπιστη πρόβλεψη.",
          "🟡 Μέτρια πρόβλεψη.",
          "🔴 Αβέβαιη πρόβλεψη."
        ] },
        { term: "xP ±std", full: "Εύρος λάθους", def: "Στο modal δίπλα στο xP εμφανίζεται ±X. Είναι το ιστορικό σφάλμα του μοντέλου για τη θέση. Μικρότερο = πιο σίγουρη πρόβλεψη." },
      ],
    },
    {
      id: "concepts",
      title: "Concepts",
      entries: [
        { term: "SFP full / partial", full: "", def: [
          "✅ Full: όλα τα components διαθέσιμα (με FR & BLA από BasketStories).",
          "⚠️ Partial: λείπει FR ή BLA → υποεκτιμημένος αριθμός."
        ] },
        { term: "Predicted vs Stats-only", full: "", def: "Predicted: έχει xP. Stats-only: μόνο στατιστικά." },
      ],
    },
    {
      id: "model",
      title: "Μοντέλο",
      entries: [
        { term: "Ensemble", full: "", def: "Συνδυάζει Ridge + Gradient Boosting + Moving Average ανά θέση (G/F/C)." },
        { term: "DVP", full: "Defense vs Position", def: "Πόσο καλά αμύνεται ο αντίπαλος στη θέση." },
      ],
    },
  ];

  // ---------------- normalization (players) ----------------
  function normalize(raw) {
    const arr = toArray(raw);
    const seen = new Set();
    const out = [];
    const stats = window.PLAYER_STATS_2026 || {};
    const tc = window.PLAYER_TREND_CONFIDENCE || {};
    const injuries = window.PLAYER_INJURIES || {};

    for (const p of arr) {
      if (!p || typeof p !== "object") continue;
      const name = pname(p).trim().toUpperCase();
      if (!name || seen.has(name)) continue;
      seen.add(name);

      const xp = num(p.xpdk_v4_2 ?? p.xpdk_v3 ?? p.xpdk ?? p.xp, 0);
      const s26 = stats[name] || {};
      const g2026 = num(s26.games_2026, 0);
      if (!xp && !g2026) continue;

      const t = tc[name] || {};
      const inj = injuries[name] || {};
      const injStatus = inj.status || "";

      out.push({
        name, xp,
        gp:        num(p.gp),
        floor:     num(p.floor_pdk),
        ceiling:   num(p.ceiling_pdk),
        cv:        num(p.cv),
        ewma5:     num(p.ewma5_pdk),
        trendLabel:p.min_trend_label || "—",
        confidence:p.confidence || "—",
        position:  (p.position || p.position_norm || s26.position || "—").toString().toUpperCase(),
        team:      p.team && p.team !== "—" ? p.team : (s26.team || "—"),
        code:      p.player_code || "—",
        g2026,
        pir:       num(s26.pir),
        avgMin:    num(s26.avg_min),
        sfp:       num(s26.sfp),
        sfpFull:   s26.sfp_full === true,
        fgPct:     num(s26.fg_pct),
        next3:     s26.next3 || [],
        credits:   num(s26.credits),
        value:     num(s26.value),
        usage:     num(s26.usage),
        trend:     t.trend || "Stable",
        trendIcon: t.trend_icon || "→",
        confEmoji: t.conf_emoji || "",
        residualStd: num(t.residual_std),
        injuryStatus: injStatus,
        injuryRound:  inj.round || "",
        isInjured:    injStatus === "out",
        isReduced:    ["uncertain", "game_time", "doubtful"].includes(injStatus),
        raw:       p,
      });
    }
    return out;
  }

  // ---------------- filtering / sorting ----------------
  function apply() {
    const q = state.query.trim().toUpperCase();
    let rows = state.players.slice();
    if (q) rows = rows.filter(r => r.name.includes(q) || String(r.team).toUpperCase().includes(q));

    if (state.positions.length < 3) {
      rows = rows.filter(r =>
        r.position === "?" || state.positions.includes(r.position)
      );
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
      return String(av).localeCompare(String(bv)) * dir;
    });
    state.filtered = rows;
  }

  function applyCoaches() {
    const q = state.coachQuery.trim().toUpperCase();
    let rows = state.coaches.slice();

    if (q) {
      rows = rows.filter(r =>
        r.name.toUpperCase().includes(q) ||
        r.team.toUpperCase().includes(q) ||
        r.teamFull.toUpperCase().includes(q)
      );
    }

    const dir = state.coachSortDir === "asc" ? 1 : -1;
    const k = state.coachSortKey;
    rows.sort((a, b) => {
      const av = a[k], bv = b[k];
      if (typeof av === "number" && typeof bv === "number") {
        if (isNaN(av)) return 1;
        if (isNaN(bv)) return -1;
        return (av - bv) * dir;
      }
      return String(av || "").localeCompare(String(bv || "")) * dir;
    });
    state.coachFiltered = rows;
  }

  // ---------------- styles ----------------
  function injectStyles() {
    if (document.getElementById("fz-styles")) return;
    const s = document.createElement("style");
    s.id = "fz-styles";
    s.textContent = `
      .fz-wrap { padding: 0; font-family: inherit; color: inherit; }

      .fz-toolbar {
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

      .fz-search-wrap {
        position:relative; display:flex; align-items:center;
        flex:1 1 260px; max-width:360px;
        background: var(--card,#fff);
        border:1px solid var(--line,#d1d5db);
        border-radius:999px;
        padding:0 14px;
        transition: border-color .15s, box-shadow .15s;
      }
      .fz-search-wrap:focus-within {
        border-color:#f97316;
        box-shadow: 0 0 0 3px rgba(249,115,22,.15);
      }
      .fz-search-icon {
        font-size:13px; opacity:.7; margin-right:6px; user-select:none;
      }
      .fz-search-wrap input {
        flex:1; border:0; outline:0; background:transparent; color:inherit;
        font-size:14px; padding:8px 0; min-width:0;
      }

      .fz-pos-group { display:flex; gap:6px; }
      .fz-pos-btn {
        padding:6px 14px; border-radius:999px; cursor:pointer;
        font-size:13px; font-weight:600;
        background: var(--card,#fff); color: inherit;
        border:1px solid var(--line,#e5e7eb);
        transition: all .15s ease;
      }
      .fz-pos-btn:hover {
        border-color:#f97316; color:#f97316;
      }
      .fz-pos-btn.on {
        background:#f97316; color:#fff; border-color:#f97316;
        box-shadow: 0 3px 10px rgba(249,115,22,.35);
      }
      .fz-pos-btn.coach-btn {
        margin-left:4px;
      }
      .fz-pos-btn.coach-btn.on {
        background:#7c3aed; border-color:#7c3aed;
        box-shadow: 0 3px 10px rgba(124,58,237,.35);
      }

      .fz-count {
        margin-left:auto; font-size:13px; opacity:.75;
        white-space:nowrap;
      }
      .fz-glossary-btn {
        display:inline-flex; align-items:center; gap:6px;
        padding:6px 14px; border-radius:999px;
        border:1px solid var(--line,#e5e7eb);
        background: var(--card,#fff); color: inherit;
        font-size:13px; font-weight:600; cursor:pointer;
        transition: all .15s ease;
        white-space:nowrap;
      }
      .fz-glossary-btn:hover {
        border-color:#f97316; color:#f97316;
      }

      .fz-table { width:100%; border-collapse: collapse; font-size:14px; }
      .fz-table th, .fz-table td { padding:8px 10px; text-align:left; border-bottom:1px solid var(--line,#e5e7eb); }
      .fz-table th { cursor:pointer; user-select:none; font-weight:600; white-space:nowrap; font-size:12px; text-transform:uppercase; letter-spacing:.03em; }
      .fz-table th:hover { color: var(--accent,#2563eb); }
      .fz-table th .arrow { font-size:11px; opacity:.6; margin-left:4px; }
      .fz-table tbody tr { cursor:pointer; }
      .fz-table tr:hover td { background: var(--hover,#f3f4f6); }
      .fz-num { text-align:right; font-variant-numeric: tabular-nums; }
      .fz-rank { width:40px; }
      td.fz-rank { opacity:.6; }
      .fz-xp { font-weight:700; color: #2563eb; }
      .fz-pir { font-weight:700; color:#f97316; }
      .fz-muted { opacity:.4; }
      .fz-badge { padding:2px 8px; border-radius:999px; font-size:11px; font-weight:600; text-transform:uppercase; }
      .fz-badge-high { background:#dcfce7; color:#166534; }
      .fz-badge-med  { background:#fef9c3; color:#854d0e; }
      .fz-badge-low  { background:#fee2e2; color:#991b1b; }
      .fz-up { color:#16a34a; } .fz-down { color:#dc2626; } .fz-flat { opacity:.6; }
      .fz-empty { padding:40px; text-align:center; opacity:.6; }
      .fz-opp { display:inline-block; padding:2px 6px; margin-right:3px; border-radius:4px; font-size:11px; font-weight:600; }
      .fz-opp.h { background:#dcfce7; color:#166534; }
      .fz-opp.a { background:#fecaca; color:#991b1b; }
      .fz-dot { display:inline-block; width:7px; height:7px; border-radius:50%; margin-left:5px; vertical-align:middle; }
      .fz-next3 { white-space:nowrap; }

      .fz-xp-col {
        background: color-mix(in srgb, #2563eb 7%, var(--card, #fff));
      }
      th.fz-xp-col {
        background: color-mix(in srgb, #2563eb 14%, var(--card, #fff));
      }
      [data-theme="dark"] .fz-xp-col {
        background: color-mix(in srgb, #60a5fa 10%, var(--card, #000));
      }
      [data-theme="dark"] th.fz-xp-col {
        background: color-mix(in srgb, #60a5fa 20%, var(--card, #000));
      }

      .fz-name-badge { margin-left:6px; font-size:13px; font-weight:700; white-space:nowrap; }
      .fz-name-badge .up { color:#16a34a; }
      .fz-name-badge .down { color:#dc2626; }
      .fz-name-badge .flat { opacity:.55; }

      /* --- INJURY BADGES --- */
      .fz-inj-badge {
        display:inline-block; font-size:11px; font-weight:800;
        padding:1px 6px; border-radius:4px; margin-left:6px;
        vertical-align:middle; letter-spacing:0.5px;
      }
      .fz-inj-badge.out { background:#dc2626; color:#fff; }
      .fz-inj-badge.reduced { background:#f59e0b; color:#000; }
      tr.fz-inj-out td { opacity:0.55; }
      tr.fz-inj-out:hover td { background: rgba(220,38,38,0.08) !important; }

      /* --- Modal --- */
      .fz-modal-bg { position:fixed; inset:0; background:rgba(0,0,0,.5); display:flex; align-items:center; justify-content:center; z-index:9999; padding:20px; }
      .fz-modal { background:var(--card,#fff); color:inherit; border-radius:14px; max-width:640px; width:100%; max-height:85vh; overflow:auto; padding:24px; box-shadow:0 20px 60px rgba(0,0,0,.3); position:relative; }
      .fz-modal h2 { margin:0 0 4px 0; font-size:22px; }
      .fz-modal .fz-sub { opacity:.7; font-size:13px; margin-bottom:16px; }
      .fz-modal-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:10px 20px; margin:16px 0; }
      .fz-modal-grid > div { display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid var(--line,#eee); }
      .fz-modal-grid span:first-child { opacity:.7; }
      .fz-close { position:absolute; top:14px; right:18px; background:transparent; border:0; font-size:22px; cursor:pointer; color:inherit; }
      .fz-log-header { display:flex; justify-content:space-between; align-items:center; margin-top:18px; padding-top:14px; border-top:2px solid var(--line,#eee); }
      .fz-log-toggle { display:flex; gap:4px; }
      .fz-log-toggle button { padding:4px 12px; border:1px solid var(--line,#ddd); background:transparent; color:inherit; border-radius:6px; cursor:pointer; font-size:12px; font-weight:600; }
      .fz-log-toggle button.on { background:var(--accent,#2563eb); color:#fff; border-color:var(--accent,#2563eb); }
      .fz-log-stats { display:flex; gap:18px; margin:10px 0; font-size:13px; opacity:.85; flex-wrap:wrap; }
      .fz-log-table { width:100%; border-collapse:collapse; font-size:12.5px; margin-top:6px; }
      .fz-log-table th, .fz-log-table td { padding:6px 8px; text-align:left; border-bottom:1px solid var(--line,#eee); white-space:nowrap; }
      .fz-log-table th { font-weight:600; font-size:11px; text-transform:uppercase; opacity:.7; }

      .fz-glossary-overlay {
        position:fixed; inset:0; background:rgba(0,0,0,.45);
        z-index:10000; opacity:0; transition:opacity .2s ease;
      }
      .fz-glossary-overlay.open { opacity:1; }
      .fz-glossary-panel {
        position:fixed; top:0; right:0; height:100vh; width:440px; max-width:92vw;
        background:var(--card,#fff); color:inherit;
        box-shadow:-8px 0 32px rgba(0,0,0,.25);
        z-index:10001; display:flex; flex-direction:column;
        transform:translateX(100%); transition:transform .25s ease;
      }
      .fz-glossary-panel.open { transform:translateX(0); }
      .fz-glossary-head {
        display:flex; justify-content:space-between; align-items:center;
        padding:18px 22px; border-bottom:1px solid var(--line,#eee);
        position:sticky; top:0; background:inherit; z-index:2;
      }
      .fz-glossary-head h2 { margin:0; font-size:18px; }
      .fz-glossary-close {
        background:transparent; border:0; font-size:24px; line-height:1;
        cursor:pointer; color:inherit; padding:0 4px;
      }
      .fz-glossary-nav {
        display:flex; gap:8px; flex-wrap:wrap;
        padding:12px 22px; border-bottom:1px solid var(--line,#eee);
        background:var(--bg,#f9fafb);
      }
      .fz-glossary-nav a {
        font-size:12px; font-weight:600; text-decoration:none;
        padding:4px 10px; border-radius:999px;
        background:var(--card,#fff); color:inherit;
        border:1px solid var(--line,#e5e7eb);
      }
      .fz-glossary-nav a:hover { border-color:#f97316; color:#f97316; }
      .fz-glossary-body { padding:8px 22px 32px; overflow-y:auto; flex:1; }
      .fz-glossary-section { margin-top:20px; scroll-margin-top:70px; }
      .fz-glossary-section h3 {
        font-size:13px; text-transform:uppercase; letter-spacing:.06em;
        opacity:.6; margin:0 0 10px 0; font-weight:700;
      }
      .fz-glossary-term { padding:12px 0; border-bottom:1px solid var(--line,#eee); }
      .fz-glossary-term:last-child { border-bottom:0; }
      .fz-glossary-term .t { font-weight:700; font-size:14px; display:block; margin-bottom:2px; }
      .fz-glossary-term .t .full { font-weight:400; font-size:12px; opacity:.65; margin-left:6px; }
      .fz-glossary-term .d { font-size:13px; opacity:.85; line-height:1.5; }
      .fz-glossary-foot {
        padding:12px 22px; border-top:1px solid var(--line,#eee);
        font-size:11px; opacity:.55; text-align:center;
      }

      .fz-credits { font-weight:700; color:#f97316; }
      .fz-cxp { font-weight:700; }
      .fz-xp-great   { color:#16a34a; }
      .fz-xp-good    { color:#22c55e; }
      .fz-xp-neutral { color:inherit; opacity:.75; }
      .fz-xp-bad     { color:#dc2626; }
      .fz-form { font-size:11px; margin-left:4px; }
      .fz-form.up   { color:#16a34a; }
      .fz-form.down { color:#dc2626; }
      .fz-form.flat { opacity:.5; }
      .fz-history-table { width:100%; border-collapse:collapse; font-size:12.5px; margin-top:8px; }
      .fz-history-table th, .fz-history-table td { padding:6px 8px; text-align:left; border-bottom:1px solid var(--line,#eee); white-space:nowrap; }
      .fz-history-table th { font-weight:600; font-size:11px; text-transform:uppercase; opacity:.7; }
      .fz-history-table .won { color:#16a34a; font-weight:700; }
      .fz-history-table .lost { color:#dc2626; font-weight:700; }

      #view-fantasy th {
        top: 61px !important;
        z-index: 100 !important;
        background: var(--card, #fff) !important;
      }
      #view-fantasy th.fz-xp-col {
        background: color-mix(in srgb, #2563eb 14%, var(--card, #fff)) !important;
      }
      [data-theme="dark"] #view-fantasy th.fz-xp-col {
        background: color-mix(in srgb, #60a5fa 20%, var(--card, #111c2e)) !important;
      }
    `;
    document.head.appendChild(s);
  }

  // ============================================================
  // TOOLBAR
  // ============================================================
  function toolbarHTML(opts) {
    const inCoach = opts.mode === "coaches";

    const posCls = p => (!inCoach && opts.positions.includes(p)) ? "on" : "";
    const coachCls = inCoach ? "on" : "";

    return `
      <div class="fz-toolbar">
        <div class="fz-search-wrap">
          <span class="fz-search-icon">🔍</span>
          <input id="fzSearch" type="text" placeholder="${esc(opts.searchPlaceholder)}" value="${esc(opts.query)}">
        </div>
        <div class="fz-pos-group">
          <button type="button" class="fz-pos-btn ${posCls("C")}" data-pos="C">Center</button>
          <button type="button" class="fz-pos-btn ${posCls("F")}" data-pos="F">Forward</button>
          <button type="button" class="fz-pos-btn ${posCls("G")}" data-pos="G">Guard</button>
          <button type="button" class="fz-pos-btn coach-btn ${coachCls}" data-pos="COACH">Coach</button>
        </div>
        <span class="fz-count">${opts.count} / ${opts.total} ${inCoach ? "coaches" : "παίκτες"}</span>
        <button id="fzGlossaryBtn" class="fz-glossary-btn" type="button">📖 Οδηγίες</button>
      </div>
    `;
  }

  function attachToolbarEvents(root) {
    const search = root.querySelector("#fzSearch");
    if (search) {
      search.addEventListener("input", e => {
        if (state.mode === "coaches") {
          state.coachQuery = e.target.value;
          applyCoaches(); renderCoachesTable();
        } else {
          state.query = e.target.value;
          apply(); renderTable();
        }
        const el = document.getElementById("fzSearch");
        if (el) { el.focus(); el.setSelectionRange(el.value.length, el.value.length); }
      });
    }

    root.querySelectorAll(".fz-pos-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const p = btn.dataset.pos;

        if (p === "COACH") {
          state.mode = (state.mode === "coaches") ? "players" : "coaches";
          renderFantasy();
          return;
        }

        if (state.mode === "coaches") {
          state.mode = "players";
          renderFantasy();
          return;
        }

        const idx = state.positions.indexOf(p);
        if (idx >= 0) state.positions.splice(idx, 1);
        else state.positions.push(p);
        apply(); renderTable();
      });
    });

    const gbtn = root.querySelector("#fzGlossaryBtn");
    if (gbtn) gbtn.addEventListener("click", openGlossary);
  }

  // ============================================================
  // RENDER — Player mode
  // ============================================================
  function renderTable() {
    const root = document.getElementById("view-fantasy");
    if (!root) return;
    const rows = state.filtered;

    const col = k => rows.map(r => r[k]).filter(v => isFinite(v));
    const arrPir    = col("pir");
    const arrAvgMin = col("avgMin");
    const arrSfp    = col("sfp");
    const arrFg     = col("fgPct");
    const arrXp     = col("xp");
    const arrUsage  = col("usage");

    function dot(val, arr) {
      if (!isFinite(val) || arr.length < 3) return "";
      const sorted = arr.slice().sort((a, b) => a - b);
      const idx = sorted.findIndex(v => v >= val);
      const pct = idx / (sorted.length - 1);
      const c = pct >= 0.66 ? '#22c55e' : pct >= 0.33 ? '#eab308' : '#ef4444';
      return `<span class="fz-dot" style="background:${c}" title="Percentile: ${Math.round(pct*100)}%"></span>`;
    }

    const arrowFor = k => state.sortKey === k ? (state.sortDir === "asc" ? "▲" : "▼") : "";

    const thead = `
      <tr>
        <th class="fz-rank">#</th>
        <th data-sort="name" title="Όνομα παίκτη">Player <span class="arrow"></span></th>
        <th data-sort="position" title="Θέση">Pos <span class="arrow"></span></th>
        <th title="Επόμενοι 3 αντίπαλοι">Next 3</th>
        <th data-sort="pir" class="fz-num" title="PIR per game (2026)">PIR <span class="arrow"></span></th>
        <th data-sort="xp" class="fz-num fz-xp-col" title="Πρόβλεψη επόμενου αγώνα">xP <span class="arrow"></span></th>
        <th data-sort="credits" class="fz-num" title="Fantasy Credits">Credits <span class="arrow"></span></th>
        <th data-sort="value" class="fz-num" title="Value = PIR / Credits">Value <span class="arrow"></span></th>
        <th data-sort="avgMin" class="fz-num" title="Μέσος χρόνος συμμετοχής">Avg MIN <span class="arrow"></span></th>
        <th data-sort="sfp" class="fz-num" title="SFP (2026)">SFP <span class="arrow"></span></th>
        <th data-sort="usage" class="fz-num" title="Usage %">Usage <span class="arrow"></span></th>
        <th data-sort="fgPct" class="fz-num" title="Field Goal %">FG% <span class="arrow"></span></th>
        <th data-sort="team" title="Ομάδα">Team <span class="arrow"></span></th>
      </tr>`;

    const tbody = rows.length
      ? rows.map((r, i) => {
          const next3 = (r.next3 || []).map(o =>
            `<span class="fz-opp ${o.home ? 'h' : 'a'}" title="${o.home ? 'Home' : 'Away'}">${o.opp}</span>`
          ).join("");
          return `
        <tr data-name="${esc(r.name)}" class="${r.isInjured ? 'fz-inj-out' : ''}">
          <td class="fz-rank">${i + 1}</td>
          <td><strong>${esc(r.name)}</strong>${nameBadge(r)}${injuryBadgeHtml(r)}</td>
          <td>${esc(r.position)}</td>
          <td class="fz-next3">${next3 || "—"}</td>
          <td class="fz-num fz-pir">${fmt(r.pir, 1)}${dot(r.pir, arrPir)}</td>
          <td class="fz-num fz-xp fz-xp-col">${r.xp ? fmt(r.xp, 1) : "—"}${dot(r.xp, arrXp)}</td>
          <td class="fz-num">${r.credits != null ? fmt(r.credits, 2) : "—"}</td>
          <td class="fz-num">${r.value != null ? fmt(r.value, 3) : "—"}</td>
          <td class="fz-num">${fmt(r.avgMin, 1)}${dot(r.avgMin, arrAvgMin)}</td>
          <td class="fz-num">${fmt(r.sfp, 1)}${r.sfpFull ? ' ✅' : ' ⚠️'}${dot(r.sfp, arrSfp)}</td>
          <td class="fz-num">${r.usage != null ? r.usage.toFixed(1) + "%" : "—"}${dot(r.usage, arrUsage)}</td>
          <td class="fz-num">${r.fgPct != null ? r.fgPct + "%" : "—"}${dot(r.fgPct, arrFg)}</td>
          <td>${esc(r.team)}</td>
        </tr>`;
        }).join("")
      : `<tr><td colspan="13" class="fz-empty">Δεν βρέθηκαν παίκτες. Δοκίμασε διαφορετικά φίλτρα.</td></tr>`;

    root.innerHTML = `
      <div class="fz-wrap">
        ${toolbarHTML({
          count: rows.length,
          total: state.players.length,
          query: state.query,
          searchPlaceholder: "Αναζήτηση παίκτη ή ομάδας...",
          mode: "players",
          positions: state.positions,
        })}
        <table class="fz-table">
          <thead>${thead}</thead>
          <tbody>${tbody}</tbody>
        </table>
      </div>`;

    root.querySelectorAll("th[data-sort]").forEach(th => {
      const el = th.querySelector(".arrow");
      if (el) el.textContent = arrowFor(th.dataset.sort);
    });

    attachToolbarEvents(root);

    root.querySelectorAll("th[data-sort]").forEach(th => {
      th.addEventListener("click", () => {
        const k = th.dataset.sort;
        if (state.sortKey === k) state.sortDir = state.sortDir === "asc" ? "desc" : "asc";
        else { state.sortKey = k; state.sortDir = ["name","team","position"].includes(k) ? "asc" : "desc"; }
        apply(); renderTable();
      });
    });
    root.querySelectorAll("tbody tr[data-name]").forEach(tr => {
      tr.addEventListener("click", () => {
        const p = state.players.find(x => x.name === tr.dataset.name);
        if (p) openModal(p);
      });
    });
  }

  // ============================================================
  // RENDER — Coach mode
  // ============================================================
  function renderCoachesTable() {
    const root = document.getElementById("view-fantasy");
    if (!root) return;
    const rows = state.coachFiltered;

    const arrowFor = k => state.coachSortKey === k ? (state.coachSortDir === "asc" ? "▲" : "▼") : "";

    const thead = `
      <tr>
        <th class="fz-rank">#</th>
        <th data-sort="name">Coach <span class="arrow">${arrowFor("name")}</span></th>
        <th data-sort="team">Team <span class="arrow">${arrowFor("team")}</span></th>
        <th data-sort="nationality">Nat <span class="arrow">${arrowFor("nationality")}</span></th>
        <th data-sort="age" class="fz-num">Age <span class="arrow">${arrowFor("age")}</span></th>
        <th data-sort="credits" class="fz-num">Credits <span class="arrow">${arrowFor("credits")}</span></th>
        <th data-sort="games" class="fz-num">GP <span class="arrow">${arrowFor("games")}</span></th>
        <th data-sort="wins" class="fz-num">W <span class="arrow">${arrowFor("wins")}</span></th>
        <th data-sort="losses" class="fz-num">L <span class="arrow">${arrowFor("losses")}</span></th>
        <th data-sort="winPct" class="fz-num">Win% <span class="arrow">${arrowFor("winPct")}</span></th>
        <th data-sort="avgXp" class="fz-num">Avg xP <span class="arrow">${arrowFor("avgXp")}</span></th>
        <th data-sort="form" class="fz-num">Form <span class="arrow">${arrowFor("form")}</span></th>
        <th data-sort="totalXp" class="fz-num">Total xP <span class="arrow">${arrowFor("totalXp")}</span></th>
      </tr>`;

    const tbody = rows.length
      ? rows.map((r, i) => `
        <tr data-team="${esc(r.team)}">
          <td class="fz-rank">${i + 1}</td>
          <td><strong>${esc(r.name)}</strong></td>
          <td>${esc(r.team)}</td>
          <td>${esc(r.nationality)}</td>
          <td class="fz-num">${r.age != null ? r.age : "—"}</td>
          <td class="fz-num fz-credits">${fmtCredits(r.credits)}</td>
          <td class="fz-num">${r.games}</td>
          <td class="fz-num">${r.wins}</td>
          <td class="fz-num">${r.losses}</td>
          <td class="fz-num">${fmt(r.winPct, 1)}%</td>
          <td class="fz-num fz-cxp ${xpClass(r.avgXp)}">${fmt(r.avgXp, 2)}${formArrow(r.form)}</td>
          <td class="fz-num">${fmt(r.form, 2)}</td>
          <td class="fz-num ${xpClass(r.totalXp)}">${fmt(r.totalXp, 0)}</td>
        </tr>`).join("")
      : `<tr><td colspan="13" class="fz-empty">Δεν βρέθηκαν προπονητές.</td></tr>`;

    root.innerHTML = `
      <div class="fz-wrap">
        ${toolbarHTML({
          count: rows.length,
          total: state.coaches.length,
          query: state.coachQuery,
          searchPlaceholder: "Αναζήτηση προπονητή ή ομάδας...",
          mode: "coaches",
          positions: state.positions,
        })}
        <table class="fz-table">
          <thead>${thead}</thead>
          <tbody>${tbody}</tbody>
        </table>
      </div>`;

    attachToolbarEvents(root);

    root.querySelectorAll("th[data-sort]").forEach(th => {
      th.addEventListener("click", () => {
        const k = th.dataset.sort;
        if (state.coachSortKey === k) state.coachSortDir = state.coachSortDir === "asc" ? "desc" : "asc";
        else { state.coachSortKey = k; state.coachSortDir = ["name","team","nationality"].includes(k) ? "asc" : "desc"; }
        applyCoaches(); renderCoachesTable();
      });
    });

    root.querySelectorAll("tbody tr[data-team]").forEach(tr => {
      tr.addEventListener("click", () => {
        const team = tr.dataset.team;
        const c = state.coaches.find(x => x.team === team);
        if (c) openCoachModal(c);
      });
    });
  }

  // ---------------- glossary ----------------
  function openGlossary() {
    closeGlossary();

    const overlay = document.createElement("div");
    overlay.className = "fz-glossary-overlay";
    overlay.addEventListener("click", closeGlossary);

    const panel = document.createElement("aside");
    panel.className = "fz-glossary-panel";
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-modal", "true");
    panel.setAttribute("aria-label", "Οδηγίες και Glossary");

    const nav = GLOSSARY.map(s =>
      `<a href="#fzg-${s.id}" data-target="fzg-${s.id}">${esc(s.title)}</a>`
    ).join("");

    const body = GLOSSARY.map(s => `
      <section class="fz-glossary-section" id="fzg-${s.id}">
        <h3>${esc(s.title)}</h3>
        ${s.entries.map(e => `
          <div class="fz-glossary-term">
            <span class="t">${esc(e.term)}${e.full ? `<span class="full">${esc(e.full)}</span>` : ""}</span>
            <div class="d">${Array.isArray(e.def) ? e.def.map(line => esc(line)).join("<br><br>") : e.def}</div>
          </div>
        `).join("")}
      </section>
    `).join("");

    panel.innerHTML = `
      <div class="fz-glossary-head">
        <h2>📖 Οδηγίες & Glossary</h2>
        <button class="fz-glossary-close" type="button" aria-label="Κλείσιμο">×</button>
      </div>
      <nav class="fz-glossary-nav">${nav}</nav>
      <div class="fz-glossary-body">${body}</div>
      <div class="fz-glossary-foot">EuroLeague Fantasy · 2026</div>
    `;

    document.body.appendChild(overlay);
    document.body.appendChild(panel);
    state.glossaryEl = { overlay, panel };

    requestAnimationFrame(() => {
      overlay.classList.add("open");
      panel.classList.add("open");
    });

    panel.querySelector(".fz-glossary-close").addEventListener("click", closeGlossary);
    panel.querySelectorAll(".fz-glossary-nav a").forEach(a => {
      a.addEventListener("click", (ev) => {
        ev.preventDefault();
        const id = a.dataset.target;
        const target = panel.querySelector("#" + id);
        if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });

    document.addEventListener("keydown", escCloseGlossary);
  }

  function closeGlossary() {
    if (!state.glossaryEl) {
      document.removeEventListener("keydown", escCloseGlossary);
      return;
    }
    const { overlay, panel } = state.glossaryEl;
    overlay.classList.remove("open");
    panel.classList.remove("open");
    setTimeout(() => {
      overlay.remove();
      panel.remove();
    }, 260);
    state.glossaryEl = null;
    document.removeEventListener("keydown", escCloseGlossary);
  }

  function escCloseGlossary(e) { if (e.key === "Escape") closeGlossary(); }

  // ---------------- player modal ----------------
  function openModal(p) {
    closeModal();
    const bg = document.createElement("div");
    bg.className = "fz-modal-bg";
    bg.addEventListener("click", e => { if (e.target === bg) closeModal(); });

    const row = (label, val) => `<div><span>${esc(label)}</span><span>${val}</span></div>`;
    const logs = (window.PLAYER_GAMELOGS && window.PLAYER_GAMELOGS[p.name]) || [];

    const xpCell = `<strong>${p.xp ? fmt(p.xp, 1) : "—"}</strong>` +
      (isFinite(p.residualStd) ? ` <span style="opacity:.6;font-size:12px">±${fmt(p.residualStd, 1)}</span>` : "");

    // Injury row αν υπάρχει
    const injRow = p.injuryStatus
      ? row("Injury", `<span class="fz-inj-badge ${p.isInjured ? 'out' : 'reduced'}" style="margin-left:0;">${
          p.isInjured ? 'OUT' : p.injuryStatus.replace('_','-')
        }</span> <span style="opacity:.7;font-size:12px">${esc(p.injuryRound || '')}</span>`)
      : "";

    bg.innerHTML = `
      <div class="fz-modal" role="dialog" aria-modal="true">
        <button class="fz-close" aria-label="Close">×</button>
        <h2>${esc(p.name)}</h2>
        <div class="fz-sub">${esc(p.team)} · ${esc(p.position)}${isNaN(p.gp) ? "" : " · " + p.gp + " GP"}${nameBadge(p)}${injuryBadgeHtml(p)}</div>
        <div class="fz-modal-grid">
          ${row("PIR 2026", `<strong>${fmt(p.pir, 1)}</strong>`)}
          ${row("xP", xpCell)}
          ${row("Credits", p.credits != null ? fmt(p.credits, 2) : "—")}
          ${row("Value", p.value != null ? fmt(p.value, 3) : "—")}
          ${row("Avg MIN 2026", fmt(p.avgMin, 1))}
          ${row("SFP 2026", `${fmt(p.sfp, 1)} ${p.sfpFull ? '✅' : '⚠️'}`)}
          ${row("Usage %", p.usage != null ? p.usage.toFixed(1) + "%" : "—")}
          ${row("FG%", p.fgPct != null ? p.fgPct + "%" : "—")}
          ${row("Games 2026", p.g2026 || "—")}
          ${row("Trend", trendBadge(p.trendLabel))}
          ${row("Confidence", confBadge(p.confidence))}
          ${injRow}
        </div>
        <div class="fz-log-header">
          <strong>Game Log</strong>
          <div class="fz-log-toggle">
            <button data-n="3">Last 3</button>
            <button data-n="5">Last 5</button>
            <button data-n="10">Last 10</button>
          </div>
        </div>
        <div class="fz-log-body"></div>
      </div>`;

    let N = 5;
    function renderLogs() {
      const body = bg.querySelector(".fz-log-body");
      const recent = logs.slice(-N).reverse();
      if (!recent.length) {
        body.innerHTML = `<div class="fz-empty" style="padding:16px">No game logs.</div>`;
        return;
      }
      const avg = (key) => {
        const vals = recent.map(r => r[key]).filter(v => typeof v === "number" && isFinite(v));
        return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : NaN;
      };
      body.innerHTML = `
        <div class="fz-log-stats">
          <span>Avg PIR: <strong>${fmt(avg("pir"), 1)}</strong></span>
          <span>Avg MIN: <strong>${fmt(avg("min"), 1)}</strong></span>
          <span>Avg PTS: <strong>${fmt(avg("pts"), 1)}</strong></span>
          <span>Avg REB: <strong>${fmt(avg("reb"), 1)}</strong></span>
        </div>
        <table class="fz-log-table">
          <thead><tr>
            <th>S</th><th>R</th><th>Opp</th><th>H/A</th>
            <th class="fz-num">MIN</th><th class="fz-num">PIR</th>
            <th class="fz-num">PTS</th><th class="fz-num">REB</th>
            <th class="fz-num">AST</th><th class="fz-num">STL</th>
            <th class="fz-num">BLK</th><th class="fz-num">TO</th>
          </tr></thead>
          <tbody>
            ${recent.map(l => `
              <tr>
                <td>${l.season ?? "—"}</td>
                <td>${l.round ?? "—"}</td>
                <td>${esc(l.opp ?? "—")}</td>
                <td>${l.home ? "H" : "A"}</td>
                <td class="fz-num">${fmt(l.min, 1)}</td>
                <td class="fz-num fz-xp">${fmt(l.pir, 1)}</td>
                <td class="fz-num">${l.pts ?? "—"}</td>
                <td class="fz-num">${l.reb ?? "—"}</td>
                <td class="fz-num">${l.ast ?? "—"}</td>
                <td class="fz-num">${l.stl ?? "—"}</td>
                <td class="fz-num">${l.blk ?? "—"}</td>
                <td class="fz-num">${l.to ?? "—"}</td>
              </tr>`).join("")}
          </tbody>
        </table>`;
    }

    bg.querySelectorAll(".fz-log-toggle button").forEach(btn => {
      btn.addEventListener("click", () => {
        N = parseInt(btn.dataset.n, 10);
        bg.querySelectorAll(".fz-log-toggle button").forEach(b => b.classList.toggle("on", b === btn));
        renderLogs();
      });
    });
    bg.querySelector('.fz-log-toggle button[data-n="5"]').classList.add("on");
    renderLogs();

    document.body.appendChild(bg);
    state.modalEl = bg;
    bg.querySelector(".fz-close").addEventListener("click", closeModal);
    document.addEventListener("keydown", escClose);
  }

  // ---------------- coach modal ----------------
  function openCoachModal(c) {
    closeModal();
    const bg = document.createElement("div");
    bg.className = "fz-modal-bg";
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
      : `<tr><td colspan="6" class="fz-empty" style="padding:16px">Δεν υπάρχει ιστορικό.</td></tr>`;

    bg.innerHTML = `
      <div class="fz-modal" role="dialog" aria-modal="true">
        <button class="fz-close" aria-label="Close">×</button>
        <h2>${esc(c.name)}</h2>
        <div class="fz-sub">${esc(c.teamFull)} · ${esc(c.nationality)}${c.age != null ? " · " + c.age + " ετών" : ""}</div>
        <div class="fz-modal-grid">
          ${row("Credits",   `<span class="fz-credits">${fmtCredits(c.credits)}</span>`)}
          ${row("Games",     c.games)}
          ${row("Wins",      c.wins)}
          ${row("Losses",    c.losses)}
          ${row("Win %",     fmt(c.winPct, 1) + "%")}
          ${row("Avg xP",    `<span class="${xpClass(c.avgXp)}">${fmt(c.avgXp, 2)}</span>`)}
          ${row("Form L5",   fmt(c.form, 2))}
          ${row("Total xP",  `<span class="${xpClass(c.totalXp)}">${fmt(c.totalXp, 0)}</span>`)}
        </div>
        <div class="fz-log-header">
          <strong>Game History</strong>
        </div>
        <table class="fz-history-table">
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
    bg.querySelector(".fz-close").addEventListener("click", closeModal);
    document.addEventListener("keydown", escClose);
  }

  function escClose(e) { if (e.key === "Escape") closeModal(); }
  function closeModal() {
    if (state.modalEl) { state.modalEl.remove(); state.modalEl = null; }
    document.removeEventListener("keydown", escClose);
  }

  // ---------------- entry ----------------
  function renderFantasy() {
    injectStyles();
    const root = document.getElementById("view-fantasy");
    if (!root) return;

    if (!state.initialized) {
      if (!window.PLAYER_STATS_2026 && !document.getElementById("fz-stats-2026")) {
        const s = document.createElement("script");
        s.id = "fz-stats-2026";
        s.src = "js/data/player-stats-2026.js";
        s.onload = () => renderFantasy();
        document.head.appendChild(s);
        return;
      }

      const raw = discoverData();
      if (!raw) {
        root.innerHTML = `<div class="fz-wrap"><div class="fz-empty">
          Δεν βρέθηκαν δεδομένα.
        </div></div>`;
        return;
      }
      const stats = window.PLAYER_STATS_2026 || {};
      const predNames = new Set((toArray(raw)).map(p => pname(p).trim().toUpperCase()));

      const extras = Object.keys(stats)
        .filter(n => !predNames.has(n))
        .filter(n => stats[n] && stats[n].games_2026 > 0)
        .map(n => ({
          player: n, player_code: n,
          team: stats[n].team || "—",
          position_norm: stats[n].position || "—",
          xpdk_v4_2: 0, gp: 0
        }));

      state.players = normalize(toArray(raw).concat(extras));
      state.coaches = normalizeCoaches(window.COACHES || []);
      state.initialized = true;

      if (!state.players.length && !state.coaches.length) {
        root.innerHTML = `<div class="fz-wrap"><div class="fz-empty">
          Το dataset φορτώθηκε αλλά 0 εγγραφές πέρασαν το φίλτρο.
        </div></div>`;
        return;
      }
    }

    if (state.mode === "coaches") {
      applyCoaches();
      renderCoachesTable();
    } else {
      apply();
      renderTable();
    }
  }

  window.renderFantasy = renderFantasy;
})();